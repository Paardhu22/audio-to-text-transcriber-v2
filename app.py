from flask import Flask, render_template, jsonify, Response, send_from_directory, request
import sqlite3
import csv
import io
import os
import os
import transcriber

app = Flask(__name__)

# Start background transcriber
transcriber.start_transcriber()

DB_FILE = "transcriptions.db"
AUDIO_DIR = "audio_clips"

def get_transcripts(limit=None, lang=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if lang and lang != "all":
        query = "SELECT timestamp, language, text, audio_file FROM transcripts WHERE language=? ORDER BY id DESC"
        params = (lang,)
    else:
        query = "SELECT timestamp, language, text, audio_file FROM transcripts ORDER BY id DESC"
        params = ()
    if limit:
        query += f" LIMIT {limit}"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [{"timestamp": r[0], "language": r[1], "text": r[2], "audio_file": r[3]} for r in rows]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/transcribe")
def transcribe_page():
    return render_template("transcribe.html") # Renamed from old index.html

@app.route("/learning")
def learning_page():
    return render_template("learning.html")

@app.route("/hunter")
def hunter_page():
    return render_template("hunter.html")

@app.route("/api/hunter/target")
def hunter_target():
    # Return a random word to hunt for.
    # We can pick from specific tough words or validated words.
    # For fun, let's have a curated list of 'Tech' words + some random validated ones.
    hard_words = ["algorithm", "heuristic", "neural", "latency", "recursion", "compile", "syntax", "variable", "function", "array"]
    
    conn = sqlite3.connect(DB_FILE)
    try:
        # Mix in some validated words
        cursor = conn.execute("SELECT word FROM validated_words ORDER BY RANDOM() LIMIT 5")
        db_words = [row[0] for row in cursor.fetchall()]
        candidates = list(set(hard_words + db_words))
    except:
        candidates = hard_words
        
    import random
    word = random.choice(candidates)
    return jsonify({"word": word})

@app.route("/api/hunter/success", methods=["POST"])
def hunter_success():
    data = request.json or {}
    word = data.get("word")
    sentence = data.get("text")
    
    if word and sentence:
        conn = sqlite3.connect(DB_FILE)
        ts = "N/A" # Should import time if needed, or rely on DB default? using simple string
        # Let's import time properly at top or just use simple format
        import time # Just in case
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        
        conn.execute("INSERT INTO context_samples (target_word, full_sentence, timestamp) VALUES (?, ?, ?)", (word, sentence, ts))
        conn.commit()
        
        # Also increment frequency if it exists in validated
        conn.execute("UPDATE validated_words SET frequency_count = frequency_count + 1 WHERE word = ?", (word,))
        conn.commit()
        
        return jsonify({"status": "captured"})
    return jsonify({"status": "error"})

@app.route("/data")
def data():
    lang = request.args.get("lang", "all")
    return jsonify(get_transcripts(limit=20, lang=lang))

@app.route("/get_learned_words")
def get_learned_words():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Check if table exists (handled in init_db but connection might be fresh)
    try:
        cursor.execute("SELECT * FROM validated_words ORDER BY frequency_count DESC")
        rows = cursor.fetchall()
        # id, word, category, frequency_count
        return jsonify([{"id": r[0], "word": r[1], "category": r[2], "count": r[3]} for r in rows])
    except:
        return jsonify([])

@app.route("/validate_word", methods=["POST"])
def validate_word_manual():
    # Manual validation from UI (if implemented)
    data = request.json
    word = data.get("word")
    if word:
        # Save to DB
        conn = sqlite3.connect(DB_FILE)
        try:
            conn.execute("INSERT OR IGNORE INTO validated_words (word, category) VALUES (?, ?)", (word, 'manual'))
            conn.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "error", "message": "No word provided"})

@app.route("/record/start", methods=["POST"])
def start_recording_route():
    # Helper to get the lang from the request
    # Expect JSON: { "lang": "en" } or { "lang": "auto" }
    data = request.json or {}
    lang = data.get("lang", "auto")
    
    transcriber.set_target_language(lang)
    transcriber.set_recording_state(True)
    return jsonify({"status": "recording_started", "focus_mode": lang})

@app.route("/record/stop", methods=["POST"])
def stop_recording_route():
    transcriber.set_recording_state(False)
    return jsonify({"status": "recording_stopped"})

@app.route("/unknown_words")
def unknown_words():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM unknown_words ORDER BY id DESC")
    rows = cursor.fetchall()
    # id, word, context, detected_lang, confidence, status, translation, timestamp
    data = [
        {
            "id": r[0], "word": r[1], "context": r[2], "lang": r[3],
            "conf": r[4], "status": r[5], "translation": r[6], "timestamp": r[7]
        }
        for r in rows
    ]
    return jsonify(data)

@app.route("/validate_now")
def validate_now():
    # Simulate Online Validation
    # In a real app, this would match 'unknown_words' against an API.
    # Here we will just take all 'unknown_words' and approve them if they look valid (len > 2).
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get pending unknown words
    cursor.execute("SELECT word FROM unknown_words WHERE status='new'")
    words = cursor.fetchall()
    
    count = 0
    for w in words:
        word_text = w[0]
        # Fake Validation Logic: Accept if alphabetic and len > 2
        if len(word_text) > 2 and word_text.isalpha():
            cursor.execute("INSERT OR IGNORE INTO validated_words (word, category) VALUES (?, ?)", (word_text, 'auto_learned'))
            cursor.execute("UPDATE unknown_words SET status='validated' WHERE word=?", (word_text,))
            count += 1
            
    conn.commit()
    return jsonify({"status": "success", "validated_count": count})

# 🔹 Download TXT
@app.route("/download/txt")
def download_txt():
    transcripts = get_transcripts()
    output = io.StringIO()
    for t in transcripts:
        output.write(f"{t['timestamp']} [{t['language']}] - {t['text']}\n")
    return Response(output.getvalue(),
                    mimetype="text/plain",
                    headers={"Content-Disposition": "attachment;filename=transcripts.txt"})

# 🔹 Download CSV
@app.route("/download/csv")
def download_csv():
    transcripts = get_transcripts()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Language", "Transcript", "AudioFile"])
    for t in transcripts:
        writer.writerow([t['timestamp'], t['language'], t['text'], t['audio_file']])
    return Response(output.getvalue(),
                    mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=transcripts.csv"})

# 🔹 Serve audio files
@app.route("/audio_clips/<path:filename>")
def download_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
