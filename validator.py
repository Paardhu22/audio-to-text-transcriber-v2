import sqlite3
import requests
import time

DB_FILE = "transcriptions.db"

def check_internet():
    try:
        # Fast check against a reliable host
        requests.get("https://www.google.com", timeout=3)
        return True
    except:
        return False

def fetch_meaning_online(word, lang):
    """
    Mock function to fetch meaning/correctness.
    In a real app, this would call OpenAI, Google Translate, or separate Dictionary API.
    Since we don't have paid keys, we will simulate or use free endpoints if possible.
    """
    # Simple Mock Logic for demonstration
    # If the word is real but low confidence, we 'validate' it.
    
    # 1. Google Translate (Unofficial/Free approach often breaks, so we fallback to mock)
    # We will just simulate a success response for now to demonstrate the flow.
    
    return {
        "valid": True,
        "translation": f"[Validated] Meaning of {word}",
        "correction": word # assuming it was correct
    }

def validate_pending_words():
    if not check_internet():
        print("⚠️ No internet connection. Skipping validation.")
        return 0

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get new words
    cursor.execute("SELECT id, word, detected_lang FROM unknown_words WHERE status='new'")
    rows = cursor.fetchall()
    
    validated_count = 0
    
    print(f"🌍 Internet connected. Validating {len(rows)} words...")
    
    for row in rows:
        row_id, word, lang = row
        
        # Simulate API call
        result = fetch_meaning_online(word, lang)
        
        if result["valid"]:
            # Update Unknown Words Table
            cursor.execute("""
                UPDATE unknown_words 
                SET status='validated', translation=? 
                WHERE id=?
            """, (result["translation"], row_id))
            
            # Feature 5: Update Vocabulary (Incremental Learning)
            # Add to vocabulary table so we know it's a "learned" word
            try:
                cursor.execute("""
                    INSERT INTO vocabulary (word, language, added_on) 
                    VALUES (?, ?, ?)
                """, (word, lang, time.strftime("%Y-%m-%d")))
            except sqlite3.IntegrityError:
                pass # Already learned
                
            validated_count += 1
            print(f"✅ Validated: {word}")
            
    conn.commit()
    conn.close()
    return validated_count

if __name__ == "__main__":
    validate_pending_words()
