from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

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
