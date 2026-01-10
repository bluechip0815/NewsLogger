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

def test_ai_connections(subscriptions):
    """Checks connections for configured AI provider/model combinations."""
    print("Testing AI connections...")

    unique_combinations = set()

    for sub in subscriptions:
        provider = sub.get('provider')
        model = sub.get('model')
        channel_name = sub.get('channel_name', 'Unknown')

        if not provider or not model:
            print(f"Error: Subscription for channel '{channel_name}' is Missing provider or model")
            continue

        unique_combinations.add((provider, model))

    for provider, model in unique_combinations:
        print(f"Testing {provider} ({model})... ", end="")

        try:
            if provider == 'google':
                gemini_key = os.getenv("GEMINI_API_KEY")
                if not gemini_key:
                    print("Skipped (GEMINI_API_KEY missing)")
                    continue

                genai.configure(api_key=gemini_key)
                gen_model = genai.GenerativeModel(model)
                response = gen_model.generate_content("Hello")
                if response:
                    print("OK")
                else:
                    print("FAILED (No response)")

            elif provider == 'openai':
                openai_key = os.getenv("OPENAI_API_KEY")
                if not openai_key:
                    print("Skipped (OPENAI_API_KEY missing)")
                    continue

                client = openai.OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Hello"}]
                )
                if response.choices[0].message.content:
                    print("OK")
                else:
                    print("FAILED (No content)")

            elif provider == 'anthropic':
                anthropic_key = os.getenv("ANTHROPIC_API_KEY")
                if not anthropic_key:
                    print("Skipped (ANTHROPIC_API_KEY missing)")
                    continue

                client = anthropic.Anthropic(api_key=anthropic_key)
                response = client.messages.create(
                    model=model,
                    max_tokens=100,
                    messages=[{"role": "user", "content": "Hello"}]
                )
                if response.content[0].text:
                    print("OK")
                else:
                    print("FAILED (No content)")

            else:
                print(f"Skipped (Unknown provider: {provider})")

        except Exception as e:
            print(f"FAILED ({e})")
