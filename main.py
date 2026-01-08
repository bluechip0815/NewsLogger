import os
import argparse
from dotenv import load_dotenv

from src.config_manager import load_configs, generate_dummy_configs
from src import database, storage, youtube, ai, tts, email_sender

# Load environment variables
load_dotenv()

def run_monitor(gen_conf, proj_conf):
    # Initialize DB
    database.init_db()

    # Get execution options
    opts = gen_conf.get('working_options', {})
    enable_tts = opts.get('enable_tts', False)
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

            # Step 2: Fetch Transcript
            transcript_file = 'step2_transcript.txt'
            # Check if we already have it
            transcript = storage.load_step_text(video_id, transcript_file)
            
            if not transcript:
                transcript = youtube.get_video_transcript(video_id)
                if transcript:
                    storage.save_step_text(video_id, transcript_file, transcript)
                else:
                    print("     (No transcript available, skipping)")
                    continue
            
            # Step 3: AI Analysis
            analysis_file = 'step3_analysis.json'
            analysis_data = storage.load_step_json(video_id, analysis_file)
            
            if not analysis_data:
                print("     -> AI Analysis running...")
                analysis_data = ai.analyze_transcript(transcript, system_prompt, user_prompt, gen_conf)
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
        print("Nothing to report.")

def main():
    parser = argparse.ArgumentParser(description="YouTube Assistant Monitor")
    parser.add_argument("--generate-config", action="store_true", help="Generate dummy configuration files if missing")
    parser.add_argument("--test-email", action="store_true", help="Send a test email")
    parser.add_argument("--test-tts", nargs=1, metavar="TEXT", help="Generate a test MP3 from the given text")

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
        print(f"Testing TTS with text: {args.test_tts[0]}")
        # Save test audio to current dir for simplicity
        tts.generate_audio_summary(args.test_tts[0], "test_audio.mp3")
    else:
        print("Starting YouTube Monitor...")
        run_monitor(gen_conf, proj_conf)

if __name__ == "__main__":
    main()
