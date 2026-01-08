import json
import os

GENERAL_CONFIG_FILE = 'general_config.json'
PROJECT_CONFIG_FILE = 'project_config.json'

def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_configs():
    if not os.path.exists(GENERAL_CONFIG_FILE) or not os.path.exists(PROJECT_CONFIG_FILE):
        raise FileNotFoundError("Configuration files not found. Run with --generate-config first.")

    gen_conf = load_json(GENERAL_CONFIG_FILE)
    proj_conf = load_json(PROJECT_CONFIG_FILE)
    return gen_conf, proj_conf

def generate_dummy_configs():
    if not os.path.exists(GENERAL_CONFIG_FILE):
        gen_data = {
            "project_name": "My YouTube Assistant",
            "email_settings": {
                "host": "smtp.example.com",
                "port": 587,
                "user": "me@example.com",
                "receiver": "you@example.com"
            },
            "ai_settings": {
                "model": "gemini-1.5-flash"
            },
            "working_options": {
                "enable_tts": True,
                "tts_lang": "en",
                "max_videos_per_channel": 3
            }
        }
        with open(GENERAL_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(gen_data, f, indent=4)
        print(f"Created {GENERAL_CONFIG_FILE}")
    else:
        print(f"{GENERAL_CONFIG_FILE} already exists.")

    if not os.path.exists(PROJECT_CONFIG_FILE):
        proj_data = {
            "system_prompt": "You are a helpful assistant. Summarize the following video transcript.",
            "subscriptions": [
                {
                    "channel_name": "Example Channel",
                    "channel_id": "UCxxxxxxxxxxxx",
                    "user_prompt": "Focus on technical details."
                }
            ]
        }
        with open(PROJECT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(proj_data, f, indent=4)
        print(f"Created {PROJECT_CONFIG_FILE}")
    else:
        # Check if we need to migrate or warn about missing fields
        pass
