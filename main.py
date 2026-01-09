import os
import argparse
from dotenv import load_dotenv

# Externe Libraries
import google.generativeai as genai
import openai
import anthropic
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from gtts import gTTS

# Load environment variables
load_dotenv()

SEEN_VIDEOS_FILE = "seen_videos.txt"

def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_seen_videos():
    if not os.path.exists(SEEN_VIDEOS_FILE):
        return set()
    with open(SEEN_VIDEOS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def save_seen_video(video_id):
    with open(SEEN_VIDEOS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{video_id}\n")

def generate_dummy_configs():
    """Generates dummy configuration files if they don't exist."""
    gen_config_file = 'general_config.json'
    proj_config_file = 'project_config.json'

    if not os.path.exists(gen_config_file):
        gen_data = {
            "project_name": "My YouTube Assistant",
            "email_settings": {
                "host": "smtp.example.com",
                "port": 587,
                "user": "me@example.com",
                "receiver": "you@example.com"
            },
            "ai_settings": {
                "provider": "gemini",
                "model": "gemini-1.5-flash"
            },
            "working_options": {
                "enable_tts": True,
                "tts_lang": "en",
                "max_videos_per_channel": 3
            }
        }
        with open(gen_config_file, 'w', encoding='utf-8') as f:
            json.dump(gen_data, f, indent=4)
        print(f"Created {gen_config_file}")
    else:
        print(f"{gen_config_file} already exists.")

    if not os.path.exists(proj_config_file):
        proj_data = {
            "subscriptions": [
                {
                    "channel_name": "Example Channel",
                    "channel_id": "UCxxxxxxxxxxxx",
                    "analysis_prompt": "Summarize this video."
                }
            ]
        }
        with open(proj_config_file, 'w', encoding='utf-8') as f:
            json.dump(proj_data, f, indent=4)
        print(f"Created {proj_config_file}")
    else:
        print(f"{proj_config_file} already exists.")

# ---------------------------------------------------------
# MODUL 1: YOUTUBE & RSS
# ---------------------------------------------------------

def get_new_videos(channel_id, seen_ids, limit=3):
    """Holt die neuesten Videos via RSS Feed."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(rss_url)
    
    new_videos = []
    
    for entry in feed.entries[:limit]:
        # Video ID aus dem yt_videoid Tag oder Link extrahieren
        video_id = getattr(entry, 'yt_videoid', None)
        if not video_id:
            continue # Fallback, falls Parsing fehlschlägt

        if video_id not in seen_ids:
            new_videos.append({
                'id': video_id,
                'title': entry.title,
                'link': entry.link,
                'published': entry.published
            })
    
    return new_videos

def get_video_transcript(video_id):
    """Zieht das Transkript mittels youtube-transcript-api."""
    try:
        # Versuche zuerst deutsche, dann englische Untertitel, dann automatisch generierte
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['de', 'en'])
        
        # Text zusammenfügen
        full_text = " ".join([t['text'] for t in transcript_list])
        return full_text
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception as e:
        print(f"Fehler beim Transkript-Abruf für {video_id}: {e}")
        return None

# ---------------------------------------------------------
# MODUL 2: KI ANALYSE (GEMINI, OPENAI, ANTHROPIC)
# ---------------------------------------------------------

def analyze_transcript(transcript_text, prompt, config):
    """Sendet Text an die konfigurierte KI zur Analyse."""
    ai_settings = config['ai_settings']
    provider = ai_settings.get('provider', 'gemini').lower()
    model_name = ai_settings.get('model')

    full_prompt = (
        f"Du bist ein hilfreicher Assistent. Deine Aufgabe: {prompt}\n\n"
        f"Hier ist das Video-Transkript:\n{transcript_text}"
    )

    if provider == 'gemini':
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY nicht in .env gefunden!")

        if not model_name:
            model_name = 'gemini-1.5-flash'

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        try:
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"KI-Analyse (Gemini) fehlgeschlagen: {e}"

    elif provider == 'openai':
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY nicht in .env gefunden!")

        if not model_name:
            model_name = 'gpt-4o'

        client = openai.OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": full_prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"KI-Analyse (OpenAI) fehlgeschlagen: {e}"

    elif provider == 'anthropic':
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY nicht in .env gefunden!")

        if not model_name:
            model_name = 'claude-3-5-sonnet-20240620'

        client = anthropic.Anthropic(api_key=api_key)

        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": full_prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            return f"KI-Analyse (Anthropic) fehlgeschlagen: {e}"

    else:
        return f"Unbekannter AI Provider: {provider}"

# ---------------------------------------------------------
# MODUL 3: TEXT-TO-SPEECH (TTS)
# ---------------------------------------------------------

def generate_audio_summary(text, video_id, lang='de'):
    """Erstellt eine MP3 Datei aus dem Text."""
    try:
        # Bereinige den Text von Markdown (einfachste Methode) für TTS
        clean_text = text.replace('*', '').replace('#', '')
        
        tts = gTTS(text=clean_text, lang=lang, slow=False)
        filename = f"summary_{video_id}.mp3"
        tts.save(filename)
        return filename
    except Exception as e:
        print(f"TTS Fehler: {e}")
        return None

# ---------------------------------------------------------
# MODUL 4: EMAIL VERSAND
# ---------------------------------------------------------

def send_email(results, general_config):
    """Versendet die HTML Email mit Audio-Anhängen."""
    email_conf = general_config['email_settings']
    msg = MIMEMultipart()
    msg['From'] = email_conf['user']
    msg['To'] = email_conf['receiver']
    msg['Subject'] = f"{general_config['project_name']} - {datetime.now().strftime('%d.%m.%Y')}"

    # HTML Body Aufbau
    html_content = "<html><body>"
    html_content += f"<h1>Dein YouTube Briefing</h1>"
    
    if not results:
        html_content += "<p>Keine neuen Videos gefunden.</p>"
    
    attachments = []

    for item in results:
        html_content += f"<hr>"
        html_content += f"<h2>{item['channel']}</h2>"
        html_content += f"<h3><a href='{item['link']}'>{item['title']}</a></h3>"
        
        # Markdown zu HTML (Simpel)
        summary_html = item['summary'].replace('\n', '<br>').replace('**', '<b>').replace('*', '<li>')
        html_content += f"<div style='background-color: #f9f9f9; padding: 15px;'>{summary_html}</div>"
        
        if item.get('audio_file'):
            html_content += f"<p><i>Audio-Zusammenfassung im Anhang: {item['audio_file']}</i></p>"
            attachments.append(item['audio_file'])

    html_content += "</body></html>"
    msg.attach(MIMEText(html_content, 'html'))

    # Audio anhängen
    for mp3_file in attachments:
        try:
            with open(mp3_file, 'rb') as f:
                audio = MIMEAudio(f.read(), _subtype="mp3")
                audio.add_header('Content-Disposition', 'attachment', filename=mp3_file)
                msg.attach(audio)
        except Exception as e:
            print(f"Konnte Anhang {mp3_file} nicht laden: {e}")

    # Senden
    try:
        password = os.getenv("EMAIL_PASSWORD")
        if not password:
            raise ValueError("EMAIL_PASSWORD nicht in .env gefunden!")

        server = smtplib.SMTP(email_conf['host'], email_conf['port'])
        server.starttls()
        server.login(email_conf['user'], password)
        server.send_message(msg)
        server.quit()
        print("E-Mail erfolgreich versendet.")
        
        # Aufräumen (Audio Dateien löschen)
        for mp3_file in attachments:
            try:
                os.remove(mp3_file)
            except:
                pass
                
        return True
    except Exception as e:
        print(f"E-Mail Sende-Fehler: {e}")
        return False

# ---------------------------------------------------------
# MAIN LOGIC
# ---------------------------------------------------------

def run_monitor(gen_conf, proj_conf):
    # Initialize DB
    database.init_db()

    # Get execution options
    opts = gen_conf.get('working_options', {})
    enable_tts = opts.get('enable_tts', False)
    allow_audio_fallback = opts.get('allow_audio_download_fallback', False)
    max_videos = opts.get('max_videos_per_channel', 3)
    system_prompt = proj_conf.get('system_prompt', "Summarize the video.")

    email_results = []

    for sub in proj_conf['subscriptions']:
        channel_name = sub['channel_name']
        channel_id = sub['channel_id']
        # Handle 'user_prompt' vs legacy 'analysis_prompt'
        user_prompt = sub.get('user_prompt', sub.get('analysis_prompt', "Focus on key points."))
        
        print(f"Checking channel: {channel_name}...")

        # Update Channel in DB
        database.upsert_channel(channel_id, channel_name, user_prompt)

        # Step 1: Fetch Metadata
        new_vids = youtube.get_new_videos(channel_id, limit=max_videos)
        
        if not new_vids:
            print("  -> No new videos.")
            continue
            
        for vid in new_vids:
            video_id = vid['id']
            video_title = vid['title']
            published = vid['published']

            # Check if processed or exists in DB
            db_video = database.get_video(video_id)
            if db_video:
                # If status is 'emailed', skip. If 'processed', maybe re-email or skip.
                # For now, let's assume if it exists in DB, we skip unless we want to retry failed steps.
                # But requirement says "next step should work on this folder".
                # Let's assume we skip if status is 'emailed'.
                if db_video[4] == 'emailed':
                    print(f"  -> Skipping processed video: {video_title}")
                    continue
            else:
                database.add_video(video_id, channel_id, video_title, published, 'new')

            print(f"  -> Processing: {video_title}")
            
            # Save Step 1 Data
            storage.save_step_json(video_id, 'step1_metadata.json', vid)

            # Step 2: Fetch Transcript or Audio (Fallback)
            transcript_file = 'step2_transcript.txt'
            transcript = storage.load_step_text(video_id, transcript_file)
            downloaded_audio_path = None

            if not transcript:
                transcript = youtube.get_video_transcript(video_id)
                if transcript:
                    storage.save_step_text(video_id, transcript_file, transcript)
                else:
                    print("     (No transcript available)")
                    # Fallback check
                    if allow_audio_fallback:
                        # Check if we already downloaded it
                        # For tracing, we might look for 'step2_audio.mp3' in the storage folder
                        fallback_audio_filename = 'step2_fallback_audio.mp3'
                        fallback_audio_path = storage.get_file_path(video_id, fallback_audio_filename)

                        if os.path.exists(fallback_audio_path):
                            print("     -> Found existing fallback audio.")
                            downloaded_audio_path = fallback_audio_path
                        else:
                            print("     -> Attempting Audio Download Fallback...")
                            # download_audio returns full path. We want to control the path.
                            downloaded_path = youtube.download_audio(video_id, fallback_audio_path)
                            if downloaded_path and os.path.exists(downloaded_path):
                                downloaded_audio_path = downloaded_path
                            else:
                                print("     (Audio download failed, skipping)")
                                continue
                    else:
                        print("     (Fallback disabled, skipping)")
                        continue

            # Step 3: AI Analysis
            analysis_file = 'step3_analysis.json'
            analysis_data = storage.load_step_json(video_id, analysis_file)
            
            if not analysis_data:
                print("     -> AI Analysis running...")
                if transcript:
                    analysis_data = ai.analyze_transcript(transcript, system_prompt, user_prompt, gen_conf)
                elif downloaded_audio_path:
                     print("     -> Analyzing Audio via Gemini...")
                     analysis_data = ai.analyze_audio(downloaded_audio_path, system_prompt, user_prompt, gen_conf)

                     # Optional: Cleanup audio if we don't want to keep it?
                     # For now, we keep it as part of the 'trace'.
                else:
                    print("     (No input data for analysis)")
                    continue

                storage.save_step_json(video_id, analysis_file, analysis_data)

                # Update DB
                database.update_video_summary(video_id, analysis_data.get('summary', ''))
                for kw in analysis_data.get('keywords', []):
                    database.add_keyword(video_id, kw)

                database.update_video_status(video_id, 'processed')

            # Step 4: TTS
            audio_path = None
            if enable_tts:
                audio_filename = 'step4_audio.mp3'
                audio_path = storage.get_file_path(video_id, audio_filename)

                if not os.path.exists(audio_path):
                    print("     -> Generating Audio...")
                    summary_text = analysis_data.get('summary', '')
                    if summary_text:
                        tts.generate_audio_summary(summary_text, audio_path, opts.get('tts_lang', 'en'))

            # Collect result for email
            email_results.append({
                'channel': channel_name,
                'title': video_title,
                'link': vid['link'],
                'id': video_id,
                'summary': analysis_data.get('summary', ''),
                'keywords': analysis_data.get('keywords', []),
                'audio_file': audio_path if enable_tts and os.path.exists(audio_path) else None
            })

    # Step 5: Report / Email
    if email_results:
        print(f"Sending report with {len(email_results)} items...")
        success = email_sender.send_email(email_results, gen_conf)
        
        if success:
            for item in email_results:
                database.update_video_status(item['id'], 'emailed')
    else:
        print("Nichts zu berichten.")

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
    success = send_email(dummy_results, gen_conf)
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
            # feedparser usually doesn't raise exceptions but sets 'bozo' bit or returns empty entries
            # If the channel ID is invalid, YouTube usually returns a 404 which feedparser handles gracefully
            # but feed.status might be useful if available (e.g. 200 vs 404)

            status = getattr(feed, 'status', None)

            if status == 200:
                print("OK")
            elif status == 404:
                print("FAILED (404 Not Found) - Check Channel ID")
            else:
                # If status is missing or other code
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


def main():
    parser = argparse.ArgumentParser(description="YouTube Assistant Monitor")
    parser.add_argument("--generate-config", action="store_true", help="Generate dummy configuration files if missing")
    parser.add_argument("--test-email", action="store_true", help="Send a test email")
    parser.add_argument("--test-tts", nargs=1, metavar="TEXT", help="Generate a test MP3 from the given text")
    parser.add_argument("--test-youtube", action="store_true", help="Check configured YouTube channels")
    parser.add_argument("--test-ai", action="store_true", help="Test connection to configured AI providers")

    args = parser.parse_args()

    if args.generate_config:
        generate_dummy_configs()
        return

    # Load configs
    try:
        gen_conf, proj_conf = load_configs()
    except Exception as e:
        print(f"Error: {e}")
        return

    if args.test_email:
        # Dummy result for testing
        print("Sending test email...")
        dummy_results = [{
            'channel': 'Test Channel',
            'title': 'Test Video Title',
            'link': 'https://www.youtube.com',
            'id': 'test_video_id',
            'summary': 'This is a test summary.',
            'keywords': ['test', 'email'],
            'audio_file': None
        }]
        email_sender.send_email(dummy_results, gen_conf)
    elif args.test_tts:
        test_tts(args.test_tts[0])
    elif args.test_youtube:
        test_youtube_channels(proj_conf)
    elif args.test_ai:
        test_ai_connections()
    else:
        print("Starting YouTube Monitor...")
        run_monitor(gen_conf, proj_conf)

if __name__ == "__main__":
    main()
