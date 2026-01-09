import feedparser
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def get_new_videos(channel_id, limit=3):
    """Fetches the latest videos via RSS Feed."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(rss_url)

    new_videos = []

    for entry in feed.entries[:limit]:
        video_id = getattr(entry, 'yt_videoid', None)
        if not video_id:
            continue

        new_videos.append({
            'id': video_id,
            'title': entry.title,
            'link': entry.link,
            'published': entry.published
        })

    return new_videos

def get_video_transcript(video_id):
    """Fetches transcript using youtube-transcript-api."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['de', 'en'])
        full_text = " ".join([t['text'] for t in transcript_list])
        return full_text
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception as e:
        print(f"Error fetching transcript for {video_id}: {e}")
        return None

def download_audio(video_id, output_path):
    """Downloads audio from a YouTube video using yt-dlp."""
    import yt_dlp

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path, # output_path includes filename
        'quiet': True,
        'noplaylist': True,
        # Force mp3 or m4a if strictly needed, but 'bestaudio' usually gives opus/m4a which gemini accepts.
        # However, yt-dlp appends the extension to outtmpl if not specified strictly.
        # To strictly force the filename to be exactly what we pass:
        'outtmpl': {'default': output_path},
        'force_filename': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    # We need to strip the extension from output_path for yt-dlp if we want the final file to have that name
    # OR we let yt-dlp handle it.
    # Actually, simpler: just download to a temp name and rename, or trust yt-dlp.
    # Let's try to just use simple download.

    try:
        # Re-defining opts for safety
        base, ext = output_path.rsplit('.', 1)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': base, # yt-dlp will add extension
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # yt-dlp automatically adds .mp3
        final_path = f"{base}.mp3"
        return final_path
    except Exception as e:
        print(f"Error downloading audio for {video_id}: {e}")
        return None
