# Scribe: Intelligent Offline Audio Transcriber 🎙️

A powerful, **offline-first** audio-to-text transcription system built with Python, Flask, and Vosk. It captures audio, detects language (English, Spanish, Hindi), and provides a modern "Glassmorphism" UI for real-time management.

## 🚀 Key Features

*   **🔒 Fully Offline**: No internet required for transcription. Your data stays on your device.
*   **🌍 Multi-Language Support**: Supports English (`en`), Spanish (`es`), and Hindi (`hi`).
*   **🎯 Focus Mode**: Select a specific language to drastically improve accuracy and reduce "hallucinations".
*   **🧠 Incremental Learning**: Detects unknown words and allows you to "validate" them online to build a custom vocabulary(still under development).
*   **📂 Export Data**: Download your transcripts as `.txt` or `.csv`.

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

### 4. 📥 Download AI Models (CRITICAL STEP)
Since the AI models are large, they are **not included** in the GitHub repo. You must download them manually.

**Recommended Models (High Accuracy - ~1.5GB each):**
1.  **English**: [Download vosk-model-en-us-0.22](https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip)
2.  **Hindi**: [Download vosk-model-hi-0.22](https://alphacephei.com/vosk/models/vosk-model-hi-0.22.zip)
3.  **Spanish**: [Download vosk-model-es-0.42](https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip)

**Setup Instructions:**
1.  Download the `.zip` files for the languages you want.
2.  **Extract** them directly into the project folder.
3.  **Renaming is NOT required**. The system automatically detects folders like `vosk-model-en-us-0.22` or `vosk-model-small-en-us...`.

---

## 🎬 How to Run

1.  Open your terminal in the project folder.
2.  Start the application:
    ```bash
    python app.py
    ```
    *You should see `✅ Loaded ... model` messages if your models are placed correctly.*

3.  Open your web browser and go to:
    ```
    http://localhost:5000
    ```

---

## 💡 How to Use

### 1. Recording
*   **Select Focus Mode**: Use the dropdown below the mic to choose your language (e.g., "English (EN)"). This ensures the highest accuracy.
*   **Start**: Click the large **Microphone Button** 🎤. It will pulse red.
*   **Stop**: Click the button again when finished. The system will process the audio and the text will appear below.

### 2. Validation (Learning Center)
*   The system automatically flags words it is unsure about (low confidence).
*   These appear in the **Learning Center** sidebar.
*   Click **"Run Online Validation"** (requires internet) to fetch definitions/translations and mark them as valid.

### 3. Exporting
*   Use the **TXT** or **CSV** buttons in the dashboard to download your history.

---

## 🔧 Troubleshooting

*   **"No models loaded" Error**:
    *   Ensure you extracted the model folders *directly* into the project directory, not inside an extra subfolder.
    *   The structure should look like: `project_folder/vosk-model-en-us-0.22/`
    
*   **"Microphone Permission Denied"**:
    *   Make sure your browser has permission to access the microphone (though this app records via Python backend, so ensure your Terminal/Python has mic access in OS Privacy settings).

---

## 📜 License
This project is open-source. Feel free to modify and distribute.
