import os
import feedparser
import google.generativeai as genai
import openai
import anthropic
from gtts import gTTS
from src import email_sender

def test_email_config(gen_conf):
    """Sends a test email to verify configuration."""
    print("Sending test email...")
    dummy_results = [{
        'channel': 'Test Channel',
        'title': 'Test Video Title',
        'link': 'https://www.youtube.com',
        'id': 'test_video_id',
        'summary': 'This is a test summary for the email configuration check.',
        'audio_file': None
    }]
    success = email_sender.send_email(dummy_results, gen_conf)
    if success:
        print("Test email sent successfully.")
    else:
        print("Failed to send test email.")

def test_tts(text):
    """Generates a test MP3 from input text."""
    try:
        print(f"Generating TTS for: '{text}'")
        filename = "sound-test.mp3"
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filename)
        print(f"Saved: {filename}")
    except Exception as e:
        print(f"TTS Error: {e}")

def test_youtube_channels(proj_conf):
    """Checks if configured channels are reachable via RSS."""
    print("Checking YouTube channels...")
    for sub in proj_conf['subscriptions']:
        channel_id = sub['channel_id']
        name = sub['channel_name']
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        print(f"Checking '{name}' ({channel_id})...", end=" ")
        try:
            feed = feedparser.parse(rss_url)
            status = getattr(feed, 'status', None)

            if status == 200:
                print("OK")
            elif status == 404:
                print("FAILED (404 Not Found) - Check Channel ID")
            else:
                if feed.entries:
                     print("OK (Entries found)")
                elif feed.bozo:
                     print(f"WARNING (Feed parsing issue: {feed.bozo_exception})")
                else:
                     print(f"UNKNOWN (Status: {status})")
        except Exception as e:
             print(f"ERROR: {e}")

def test_ai_connections():
    """Checks connections for all configured AI secrets in .env."""
    print("Testing AI connections...")

    # 1. Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print("Checking Gemini... ", end="")
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("Hello")
            if response:
                print("OK")
            else:
                print("FAILED (No response)")
        except Exception as e:
            print(f"FAILED ({e})")
    else:
        print("Skipping Gemini (GEMINI_API_KEY not found)")

    # 2. OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("Checking OpenAI... ", end="")
        try:
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}]
            )
            if response.choices[0].message.content:
                print("OK")
            else:
                print("FAILED (No content)")
        except Exception as e:
            print(f"FAILED ({e})")
    else:
        print("Skipping OpenAI (OPENAI_API_KEY not found)")

    # 3. Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        print("Checking Anthropic... ", end="")
        try:
            client = anthropic.Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=100,
                messages=[{"role": "user", "content": "Hello"}]
            )
            if response.content[0].text:
                print("OK")
            else:
                print("FAILED (No content)")
        except Exception as e:
            print(f"FAILED ({e})")
    else:
        print("Skipping Anthropic (ANTHROPIC_API_KEY not found)")
