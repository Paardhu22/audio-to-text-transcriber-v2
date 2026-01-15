from flask import Flask, render_template, jsonify, Response, send_from_directory, request
import sqlite3
import csv
import io
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

@app.route("/data")
def data():
    lang = request.args.get("lang", "all")
    return jsonify(get_transcripts(limit=20, lang=lang))

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
    try:
        import validator
        count = validator.validate_pending_words()
        return jsonify({"status": "success", "validated_count": count})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

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
