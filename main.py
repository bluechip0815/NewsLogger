import os
import json
import smtplib
import feedparser
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from datetime import datetime
from dotenv import load_dotenv

# Externe Libraries
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from gtts import gTTS

# ---------------------------------------------------------
# SETUP & CONFIG
# ---------------------------------------------------------

# Lädt Umgebungsvariablen aus der .env Datei
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
# MODUL 2: KI ANALYSE (GEMINI)
# ---------------------------------------------------------

def analyze_transcript(transcript_text, prompt, config):
    """Sendet Text an Gemini zur Analyse."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY nicht in .env gefunden!")

    genai.configure(api_key=api_key)
    
    model_name = config['ai_settings'].get('model', 'gemini-1.5-flash')
    model = genai.GenerativeModel(model_name)

    # Prompt Engineering: Kontext setzen
    full_prompt = (
        f"Du bist ein hilfreicher Assistent. Deine Aufgabe: {prompt}\n\n"
        f"Hier ist das Video-Transkript:\n{transcript_text}"
    )

    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"KI-Analyse fehlgeschlagen: {e}"

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

def main():
    print("Starte YouTube Monitor...")
    
    # 1. Config laden
    try:
        gen_conf = load_json('general_config.json')
        proj_conf = load_json('project_config.json')
    except FileNotFoundError:
        print("Fehler: Konfigurationsdateien nicht gefunden.")
        return

    seen_videos = get_seen_videos()
    processing_results = []
    
    opts = gen_conf.get('working_options', {})
    enable_tts = opts.get('enable_tts', False)
    max_videos = opts.get('max_videos_per_channel', 3)

    # 2. Kanäle durchlaufen
    for sub in proj_conf['subscriptions']:
        print(f"Prüfe Kanal: {sub['channel_name']}...")
        
        new_vids = get_new_videos(sub['channel_id'], seen_videos, limit=max_videos)
        
        if not new_vids:
            print("  -> Keine neuen Videos.")
            continue
            
        for vid in new_vids:
            print(f"  -> Verarbeite: {vid['title']}")
            
            # Transkript holen
            transcript = get_video_transcript(vid['id'])
            
            if not transcript:
                print("     (Kein Transkript verfügbar, überspringe)")
                continue
            
            # KI Analyse
            print("     -> KI Analyse läuft...")
            summary = analyze_transcript(transcript, sub['analysis_prompt'], gen_conf)
            
            result_entry = {
                'channel': sub['channel_name'],
                'title': vid['title'],
                'link': vid['link'],
                'id': vid['id'],
                'summary': summary,
                'audio_file': None
            }

            # TTS Generierung (Optional)
            if enable_tts:
                print("     -> Generiere Audio...")
                audio_file = generate_audio_summary(summary, vid['id'], opts.get('tts_lang', 'de'))
                result_entry['audio_file'] = audio_file

            processing_results.append(result_entry)

    # 3. Bericht senden & Status updaten
    if processing_results:
        print(f"Sende Bericht mit {len(processing_results)} Analysen...")
        success = send_email(processing_results, gen_conf)
        
        if success:
            # Nur als 'gesehen' markieren, wenn Email rausging
            for item in processing_results:
                save_seen_video(item['id'])
    else:
        print("Nichts zu berichten.")

if __name__ == "__main__":
    main()