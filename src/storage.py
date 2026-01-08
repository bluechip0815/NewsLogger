import os
import json

DATA_DIR = "data"

def ensure_video_folder(video_id):
    """Creates the folder structure data/<video_id> if it doesn't exist."""
    path = os.path.join(DATA_DIR, video_id)
    os.makedirs(path, exist_ok=True)
    return path

def save_step_json(video_id, filename, data):
    folder = ensure_video_folder(video_id)
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    return filepath

def load_step_json(video_id, filename):
    folder = ensure_video_folder(video_id)
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_step_text(video_id, filename, text):
    folder = ensure_video_folder(video_id)
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    return filepath

def load_step_text(video_id, filename):
    folder = ensure_video_folder(video_id)
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def get_file_path(video_id, filename):
    return os.path.join(DATA_DIR, video_id, filename)
