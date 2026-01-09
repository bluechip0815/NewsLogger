import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from datetime import datetime

def send_email(results, general_config):
    """Sends HTML email with audio attachments."""
    email_conf = general_config['email_settings']
    msg = MIMEMultipart()
    msg['From'] = email_conf['user']
    msg['To'] = email_conf['receiver']
    msg['Subject'] = f"{general_config['project_name']} - {datetime.now().strftime('%d.%m.%Y')}"

    # HTML Body Construction
    html_content = "<html><body>"
    html_content += f"<h1>Your YouTube Briefing</h1>"

    if not results:
        html_content += "<p>No new videos processed.</p>"

    attachments = []

    for item in results:
        html_content += f"<hr>"
        html_content += f"<h2>{item['channel']}</h2>"
        html_content += f"<h3><a href='{item['link']}'>{item['title']}</a></h3>"

        # Markdown to HTML (Simple)
        summary_html = item['summary'].replace('\n', '<br>').replace('**', '<b>').replace('*', '<li>')
        html_content += f"<div style='background-color: #f9f9f9; padding: 15px;'>{summary_html}</div>"

        # Keywords
        if item.get('keywords'):
            html_content += f"<p><b>Keywords:</b> {', '.join(item['keywords'])}</p>"

        if item.get('audio_file') and os.path.exists(item['audio_file']):
            filename = os.path.basename(item['audio_file'])
            html_content += f"<p><i>Audio summary attached: {filename}</i></p>"
            attachments.append(item['audio_file'])

    html_content += "</body></html>"
    msg.attach(MIMEText(html_content, 'html'))

    # Attach Audio
    for mp3_path in attachments:
        try:
            with open(mp3_path, 'rb') as f:
                filename = os.path.basename(mp3_path)
                audio = MIMEAudio(f.read(), _subtype="mp3")
                audio.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(audio)
        except Exception as e:
            print(f"Could not attach {mp3_path}: {e}")

    # Send
    try:
        password = os.getenv("EMAIL_PASSWORD")
        if not password:
            raise ValueError("EMAIL_PASSWORD not found in .env!")

        server = smtplib.SMTP(email_conf['host'], email_conf['port'])
        server.starttls()
        server.login(email_conf['user'], password)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully.")
        return True
    except Exception as e:
        print(f"Email Send Error: {e}")
        return False
