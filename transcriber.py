import os, queue, json, sqlite3, time, threading, wave
import sounddevice as sd
import vosk

# Candidate paths to search for (Priority: Large -> Small)
MODEL_CANDIDATES = {
    "en": ["vosk-model-en-us-0.22", "vosk-model-small-en-us-0.15"],
    "es": ["vosk-model-es-0.42", "vosk-model-small-es-0.42"], 
    "hi": ["vosk-model-hi-0.22", "vosk-model-small-hi-0.22"]
}

recognizers = {}
active_models = []
recording_active = False 
target_languages = [] # Empty means "Auto" (All)

def set_target_language(lang):
    """
    lang: 'auto', 'en', 'es', 'hi'
    """
    global target_languages
    if lang == "auto" or lang not in recognizers:
        target_languages = [] # Use all
        print("🎯 Focus Mode: AUTO (All Languages)")
    else:
        target_languages = [lang]
        print(f"🎯 Focus Mode: {lang.upper()} Only")

def find_model_path(base_name):
    """
    Handle cases where user extracted 'model/' into 'model/model/' 
    or just 'model/'.
    """
    # 1. Check direct path
    if os.path.exists(os.path.join(base_name, "conf")):
        return base_name
    
    # 2. Check nested same-name folder
    nested = os.path.join(base_name, base_name)
    if os.path.exists(os.path.join(nested, "conf")):
        return nested
        
    # 3. Last ditch: check ANY subfolder
    if os.path.exists(base_name):
        for child in os.listdir(base_name):
            candidate = os.path.join(base_name, child)
            if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, "conf")):
                return candidate
    return None

print("🔄 Loading models...")
for lang, candidates in MODEL_CANDIDATES.items():
    # Try each candidate until one works
    loaded = False
    for base_path in candidates:
        final_path = find_model_path(base_path)
        if final_path:
            try:
                model = vosk.Model(final_path)
                rec = vosk.KaldiRecognizer(model, 16000)
                rec.SetWords(True) 
                recognizers[lang] = rec
                active_models.append(lang)
                print(f"✅ Loaded {lang} model from {final_path}")
                loaded = True
                break # Stop searching for this language
            except Exception as e:
                print(f"⚠️ Found {base_path} but failed to load: {e}")
        
    if not loaded:
        print(f"⚠️ No valid model found for {lang}. (Checked: {candidates})")
        
if not recognizers:
    print("❌ No models matched! automatic speech recognition will not work.")

DB_FILE = "transcriptions.db"
AUDIO_DIR = "audio_clips"
os.makedirs(AUDIO_DIR, exist_ok=True)

q = queue.Queue()

def set_recording_state(state):
    global recording_active
    recording_active = state
    print(f"🔴 Recording State Changed: {state}")
    return recording_active

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    # Transcripts Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            language TEXT,
            text TEXT,
            audio_file TEXT
        )
    """)
    # Unknown Words Table - Feature 3
    conn.execute("""
        CREATE TABLE IF NOT EXISTS unknown_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT,
            context TEXT,
            detected_lang TEXT,
            confidence REAL,
            status TEXT DEFAULT 'new', 
            translation TEXT,
            timestamp TEXT
        )
    """)
    # Vocabulary Table - Feature 5
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            language TEXT,
            added_on TEXT
        )
    """)
    conn.commit()
    return conn

conn = init_db()

def save_transcript(text, lang, audio_path=None):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO transcripts (timestamp, language, text, audio_file) VALUES (?, ?, ?, ?)",
        (ts, lang, text, audio_path)
    )
    conn.commit()

def save_unknown_word(word, context, lang, confidence):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    # Check if word already exists to avoid duplicates
    cursor = conn.execute("SELECT id FROM unknown_words WHERE word = ? AND detected_lang = ?", (word, lang))
    if not cursor.fetchone():
        conn.execute(
            "INSERT INTO unknown_words (word, context, detected_lang, confidence, timestamp) VALUES (?, ?, ?, ?, ?)",
            (word, context, lang, confidence, ts)
        )
        conn.commit()
        print(f"❓ Saved unknown/low-conf word: '{word}' ({lang})")

def save_audio_chunk(raw_data, lang):
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{lang}_{ts}.wav"
    filepath = os.path.join(AUDIO_DIR, filename)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(raw_data)
    return filepath

def audio_callback(indata, frames, time, status):
    if status:
        pass # print("Audio status:", status, flush=True)
    if recording_active:
        q.put(bytes(indata))

def transcribe_loop():
    with sd.RawInputStream(samplerate=16000, blocksize=8000,
                           dtype="int16", channels=1,
                           callback=audio_callback):
        print(f"🎤 Listening... Active Languages: {active_models}")
        
        # Track previous state to detect "Edge Trigger" of stopping
        was_recording = False
        
        while True:
            # If we are NOT recording and queue is empty, just wait (sleep) to save CPU
            if not recording_active and q.empty():
                if was_recording:
                    # Just transitioned from Recording -> Paused
                    # Flush any partial results from recognizers
                    print("🛑 Stopping... processing final fragments.")
                    for lang, rec in recognizers.items():
                        if target_languages and lang not in target_languages: continue
                        
                        # Fix for Result flush
                        # Note: Result() might not be enough if queue was cleared.
                        # But since we don't clear queue now, it should process remnants.
                        final_json = json.loads(rec.FinalResult())
                        text = final_json.get("text", "").strip()
                        if text:
                            print(f"[{lang.upper()}] FINAL: {text}")
                            save_transcript(text, lang)
                            if "result" in final_json:
                                for w_obj in final_json["result"]:
                                    word = w_obj["word"]
                                    conf = w_obj.get("conf", 1.0)
                                    if conf < 0.6 or word == "<unk>":
                                        save_unknown_word(word, text, lang, conf)

                    was_recording = False
                
                time.sleep(0.5) 
                continue
            
            # If we are recording OR there is data left in the queue, process it.
            try:
                data = q.get(timeout=0.5) 
            except queue.Empty:
                continue

            was_recording = True 
            
            # --- PROCESSING LOGIC ---
            best_lang = None
            best_text = ""
            best_score = -100000.0
            best_result_json = None
            
            candidates = []
            
            # FOCUS MODE: Only iterate over target languages if set
            langs_to_check = target_languages if target_languages else recognizers.keys()
            
            for lang in langs_to_check:
                if lang not in recognizers: continue
                rec = recognizers[lang]
                
                if rec.AcceptWaveform(data):
                    res_str = rec.Result()
                    res = json.loads(res_str)
                    text = res.get("text", "").strip()
                    if text:
                        words = res.get("result", [])
                        if words:
                            avg_conf = sum(w.get("conf", 1.0) for w in words) / len(words)
                            # Threshold Logic Check
                            # If average confidence is below 0.7, we might be hallucinating
                            if avg_conf < 0.7:
                                continue 
                                
                            score = len(text) * avg_conf
                            candidates.append({
                                "lang": lang, 
                                "text": text, 
                                "score": score, 
                                "json": res
                            })
            
            if candidates:
                candidates.sort(key=lambda x: x["score"], reverse=True)
                winner = candidates[0]
                
                best_lang = winner["lang"]
                best_text = winner["text"]
                best_json = winner["json"]
                
                audio_path = save_audio_chunk(data, best_lang)
                print(f"[{best_lang.upper()}] {best_text}  (Score: {winner['score']:.2f})")
                save_transcript(best_text, best_lang, audio_path)
                
                if "result" in best_json:
                    for w_obj in best_json["result"]:
                        word = w_obj["word"]
                        conf = w_obj.get("conf", 1.0)
                        if conf < 0.6 or word == "<unk>":
                            save_unknown_word(word, best_text, best_lang, conf)

def start_transcriber():
    if not recognizers:
        print("❌ Cannot start transcriber: No models loaded.")
        return
    t = threading.Thread(target=transcribe_loop, daemon=True)
    t.start()
