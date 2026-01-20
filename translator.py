import re

class SimpleTranslator:
    def __init__(self):
        # A simple offline dictionary for demonstration.
        # Format: {source_word: {target_lang: target_word}}
        # This is a naive word-by-word replacement + some phrases for a school project level offline demo.
        self.dictionary = {
            "hello": {"es": "hola", "hi": "नमस्ते"},
            "world": {"es": "mundo", "hi": "दुनिया"},
            "good": {"es": "bueno", "hi": "अच्छा"},
            "morning": {"es": "mañana", "hi": "सुबह"},
            "thank": {"es": "gracias", "hi": "धन्यवाद"},
            "you": {"es": "", "hi": "आप"}, # Context dependent
            "how": {"es": "cómo", "hi": "कैसे"},
            "are": {"es": "estás", "hi": "हैं"},
            "i": {"es": "yo", "hi": "मैं"},
            "am": {"es": "soy", "hi": "हूँ"},
            "fine": {"es": "bien", "hi": "ठीक"},
            "name": {"es": "nombre", "hi": "नाम"},
            "is": {"es": "es", "hi": "है"},
            "my": {"es": "mi", "hi": "मेरा"},
            "open": {"es": "abierto", "hi": "खुला"},
            "close": {"es": "cerrar", "hi": "बंद"},
            "save": {"es": "guardar", "hi": "सहेजें"},
        }

        # Phrase mappings for better quality on specific sentences
        self.phrases = {
            "how are you": {"es": "¿Cómo estás?", "hi": "आप कैसे हैं?"},
            "good morning": {"es": "Buenos días", "hi": "सुप्रभात"},
            "thank you": {"es": "Gracias", "hi": "धन्यवाद"},
            "my name is": {"es": "Mi nombre es", "hi": "मेरा नाम है"},
            "i am fine": {"es": "Estoy bien", "hi": "मैं ठीक हूँ"},
        }

    def detect_language(self, text):
        """
        Simple heuristic detection based on character ranges.
        """
        text = text.strip()
        if not text:
            return "unknown"

        # Check for Hindi (Devanagari block)
        if re.search(r'[\u0900-\u097F]', text):
            return "hi"
        
        # Check for Spanish-ish signals (accents) if not Hindi
        # Note: This is weak, but 'ñ' or '¿' are strong indicators.
        if re.search(r'[áéíóúñ¿¡]', text.lower()):
            return "es"
            
        # Default to English if ASCII and no other strong signals
        # (Real detection needs n-grams, but this is 100% offline/dependency-free)
        return "en"

    def translate(self, text, target_lang):
        """
        Translate text to target_lang.
        Supports: EN -> ES, EN -> HI. 
        For ES/HI -> EN, we'd need reverse mappings (omitted for brevity unless requested).
        """
        if not text or not target_lang:
            return ""

        detected = self.detect_language(text)
        if detected == target_lang:
            return text # Same lang

        text_lower = text.lower().strip()
        
        # 1. Try exact phrase match
        for phrase, trans in self.phrases.items():
            if phrase in text_lower:
                if target_lang in trans:
                    return trans[target_lang]

        # 2. Word-by-word (Naive)
        # Only works well for EN -> Others
        words = text.split()
        translated_words = []
        
        for w in words:
            # Strip punctuation
            clean_w = re.sub(r'[^\w\s]', '', w.lower())
            
            if clean_w in self.dictionary and target_lang in self.dictionary[clean_w]:
                translated_words.append(self.dictionary[clean_w][target_lang])
            else:
                translated_words.append(w) # Keep original if unknown

        return " ".join(translated_words)

# Singleton instance
translator = SimpleTranslator()
