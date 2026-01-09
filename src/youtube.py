import feedparser

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

def download_audio(video_id, output_path):
    """Downloads audio from a YouTube video using yt-dlp."""
    import yt_dlp

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
    }

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
