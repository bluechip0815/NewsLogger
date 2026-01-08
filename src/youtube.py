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
