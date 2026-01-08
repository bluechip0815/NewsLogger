from gtts import gTTS
import os

def generate_audio_summary(text, filepath, lang='de'):
    """Generates an MP3 file from text and saves it to the specified filepath."""
    try:
        clean_text = text.replace('*', '').replace('#', '')
        tts = gTTS(text=clean_text, lang=lang, slow=False)
        tts.save(filepath)
        return True
    except Exception as e:
        print(f"TTS Error: {e}")
        return False
