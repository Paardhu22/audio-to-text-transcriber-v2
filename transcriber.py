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
        pass 
    if recording_active:
        # Optimization: Boost volume slightly if too quiet (Simple Normalization)
        # vosk-small models struggle with low volume.
        # This is a naive boost (multiplying amplitude).
        # We process 'indata' as numpy array if we had numpy, but here it's bytes/buffer.
        # We'll just pass it through because manipulating raw bytes in Python is slow/complex without numpy.
        # Instead, relying on user to speak up or OS microphone gain.
        # However, we CAN ensure we don't drop frames.
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
                    
                    final_candidates = []
                    
                    for lang, rec in recognizers.items():
                        if target_languages and lang not in target_languages: continue
                        
                        final_json = json.loads(rec.FinalResult())
                        text = final_json.get("text", "").strip()
                        
                        if text:
                            # Calculate Score for Final Fragment
                            words = final_json.get("result", [])
                            avg_conf = 0.0
                            if words:
                                avg_conf = sum(w.get("conf", 1.0) for w in words) / len(words)
                            
                            # Base Score
                            base_score = len(text) * avg_conf
                            
                            # Linguistic Bonus (Same as main loop)
                            bonus = 0
                            text_words = set(text.lower().split())
                            matches = text_words.intersection(COMMON_WORDS.get(lang, set()))
                            if matches:
                                bonus = len(matches) * 20.0 
                            
                            final_score = base_score + bonus
                            
                            final_candidates.append({
                                "lang": lang,
                                "text": text,
                                "score": final_score,
                                "json": final_json
                            })

                    # Pick Winner for Final Fragment
                    if final_candidates:
                        final_candidates.sort(key=lambda x: x["score"], reverse=True)
                        winner = final_candidates[0]
                        print(f"[{winner['lang'].upper()}] FINAL: {winner['text']} (Score: {winner['score']:.2f})")
                        save_transcript(winner['text'], winner['lang'])
                        
                        if "result" in winner['json']:
                            for w_obj in winner['json']['result']:
                                word = w_obj["word"]
                                conf = w_obj.get("conf", 1.0)
                                if conf < 0.6 or word == "<unk>":
                                    # For unknown words, we pass the winner details
                                    save_unknown_word(word, winner['text'], winner['lang'], conf)

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
            
            # IMPROVEMENT: Linguistic Verification (Stop Words)
            # Small models hallucinate. Valid text usually contains common words.
            COMMON_WORDS = {
                "en": {"the", "is", "to", "and", "a", "of", "in", "it", "you", "that"},
                "es": {"el", "la", "de", "que", "y", "en", "un", "una", "es", "por"},
                "hi": {"है", "में", "से", "का", "की", "और", "एक", "हैं", "को", "पर"}
            }
            
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
                            # 1. Base Score: Confidence * Length
                            avg_conf = sum(w.get("conf", 1.0) for w in words) / len(words)
                            if avg_conf < 0.6: continue # Hard threshold for noise
                            
                            base_score = len(text) * avg_conf
                            
                            # 2. Linguistic Bonus: Check for stop words
                            # If the model finds "the" or "hai", it is VERY likely correct.
                            # Give massive bonus.
                            bonus = 0
                            text_words = set(text.lower().split())
                            matches = text_words.intersection(COMMON_WORDS.get(lang, set()))
                            if matches:
                                bonus = len(matches) * 20.0 # +20 points per stop word!
                            
                            final_score = base_score + bonus
                            
                            candidates.append({
                                "lang": lang, 
                                "text": text, 
                                "score": final_score, 
                                "json": res
                            })
            
            if candidates:
                candidates.sort(key=lambda x: x["score"], reverse=True)
                winner = candidates[0]
                
                best_lang = winner["lang"]
                best_text = winner["text"]
                # ... rest of saving logic ...
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
