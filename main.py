import os
import argparse
from dotenv import load_dotenv

# Import modules from src
from src import youtube, ai, tts, email_sender, storage, database, config_manager, test_utils

# Load environment variables
load_dotenv()

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


def main():
    parser = argparse.ArgumentParser(description="YouTube Assistant Monitor")
    parser.add_argument("--generate-config", action="store_true", help="Generate dummy configuration files if missing")
    parser.add_argument("--test-email", action="store_true", help="Send a test email")
    parser.add_argument("--test-tts", nargs=1, metavar="TEXT", help="Generate a test MP3 from the given text")
    parser.add_argument("--test-youtube", action="store_true", help="Check configured YouTube channels")
    parser.add_argument("--test-ai", action="store_true", help="Test connection to configured AI providers")

    args = parser.parse_args()

    if args.generate_config:
        config_manager.generate_dummy_configs()
        return

    # Load configs
    try:
        gen_conf, proj_conf = config_manager.load_configs()
    except Exception as e:
        print(f"Error: {e}")
        return

    if args.test_email:
        test_utils.test_email_config(gen_conf)
    elif args.test_tts:
        test_utils.test_tts(args.test_tts[0])
    elif args.test_youtube:
        test_utils.test_youtube_channels(proj_conf)
    elif args.test_ai:
        test_utils.test_ai_connections(proj_conf)
    else:
        print("Starting YouTube Monitor...")
        run_monitor(gen_conf, proj_conf)

if __name__ == "__main__":
    main()
