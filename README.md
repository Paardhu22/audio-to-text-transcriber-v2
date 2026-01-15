# Scribe: Intelligent Offline Audio Transcriber v2 🎙️

A powerful, **offline-first** audio-to-text transcription system built with Python, Flask, and Vosk. It captures audio, detects language (English, Spanish, Hindi), and provides a modern "Glassmorphism" UI for real-time management.

**v2 Update**: optimized for lightweight performance and high accuracy using "Smart Grammar Verification".

![Scribe Dashboard](https://i.imgur.com/your-image-placeholder.png)

## 🚀 Key Features

*   **🔒 Fully Offline**: No internet required for transcription. Your data stays on your device.
*   **🌍 Multi-Language Support**: Supports English (`en`), Spanish (`es`), and Hindi (`hi`).
*   **🎯 Focus Mode**: Select a specific language to drastically improve accuracy and reduce "hallucinations".
*   **🧠 Smart Grammar Check**: Advanced linguistic verification that boosts scores for common stop-words (e.g., "the", "hai"), ensuring gibberish is filtered out.
*   **📋 Click-to-Copy**: Click any transcript bubble to instantly copy the text to your clipboard.
*   **🎨 Premium UI**: Beautiful, responsive dashboard with animated recording controls and real-time updates.
*   **📂 Export Data**: Download your transcripts as `.txt` or `.csv`.
*   **🧪 Incremental Learning**: Detects unknown words and allows you to "validate" them online to build a custom vocabulary.

---

## 🛠️ Installation Guide

Follow these steps to set up the project on any machine (Windows, Mac, or Linux).

### 1. Prerequisites
Ensure you have **Python 3.8+** installed.
*   [Download Python](https://www.python.org/downloads/)

### 2. Clone the Repository
```bash
git clone https://github.com/Paardhu22/audio-to-text-transcriber-v2.git
cd audio-to-text-transcriber-v2
```

### 3. Install Dependencies
Install the required Python libraries:
```bash
pip install flask sounddevice vosk requests
```
*(Note for Linux users: You might need output audio backend like `sudo apt-get install libportaudio2`)*

### 4. 📥 Download AI Models
The project is optimized for **Vosk Small Models** (lightweight & fast ~50MB each).

**Required Models:**
1.  **English**: [Download vosk-model-small-en-us-0.15](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip)
2.  **Hindi**: [Download vosk-model-small-hi-0.22](https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip)
3.  **Spanish**: [Download vosk-model-small-es-0.42](https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip)

**Setup Instructions:**
1.  Download the `.zip` files for the languages you want.
2.  **Extract** them directly into the project folder.
3.  The system will auto-detect them (e.g., `vosk-model-small-en-us...`).

---

## 🎬 How to Run

1.  Open your terminal in the project folder.
2.  Start the application:
    ```bash
    python app.py
    ```
    *You should see `✅ Loaded ...` messages in the terminal.*

3.  Open your web browser and go to:
    ```
    http://localhost:5000
    ```

---

## 💡 Usage Tips

### 🎤 Best Accuracy
*   **Use Focus Mode**: Before recording, select your language from the dropdown (e.g., "English (EN)"). This disables other language models and prevents cross-talk/confusion.

### 📋 Interaction
*   **Copy Text**: Simply click on any transcript to copy it. A notification will confirm "Text Copied".
*   **Validation**: If you see words in the "Learning Center", click "Run Online Validation" (requires internet) to fetch definitions.

### 📂 File Management
*   Audio clips are saved in `audio_clips/`.
*   Database is stored in `transcriptions.db` (SQLite).

---

## 🔧 Troubleshooting

*   **"No models loaded" Error**:
    *   Ensure you extracted the model folders *directly* into the project directory.
    
*   **"Microphone Permission Denied"**:
    *   Ensure your Terminal or Python has microphone access in your OS Privacy settings.

---

## 📜 License
This project is open-source. Feel free to modify and distribute.
