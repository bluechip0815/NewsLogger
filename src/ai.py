import os
import json
import google.generativeai as genai

def analyze_transcript(transcript_text, system_prompt, user_prompt, config):
    """
    Sends text to Gemini for analysis.
    Returns a dictionary with 'summary' and 'keywords'.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env!")

    genai.configure(api_key=api_key)

    model_name = config['ai_settings'].get('model', 'gemini-1.5-flash')
    model = genai.GenerativeModel(model_name)

    # Prompt Engineering
    # We ask for a JSON response to parse summary and keywords easily
    instruction = (
        f"{system_prompt}\n"
        f"Specific instructions: {user_prompt}\n\n"
        f"Please provide the output in the following JSON format:\n"
        f"{{\n"
        f"  \"summary\": \"The summary of the video...\",\n"
        f"  \"keywords\": [\"keyword1\", \"keyword2\", ...]\n"
        f"}}\n\n"
        f"Here is the video transcript:\n{transcript_text}"
    )

    try:
        response = model.generate_content(instruction)
        text_response = response.text

        # Simple cleanup to ensure we get JSON if the model wraps it in markdown code blocks
        if text_response.startswith("```json"):
            text_response = text_response.replace("```json", "", 1)
        elif text_response.startswith("```"):
            text_response = text_response.replace("```", "", 1)

        if text_response.endswith("```"):
            text_response = text_response.rsplit("```", 1)[0]

        return json.loads(text_response.strip())
    except Exception as e:
        print(f"AI Analysis failed: {e}")
        # Return fallback structure
        return {
            "summary": f"AI Analysis failed: {e}",
            "keywords": []
        }

def analyze_audio(audio_path, system_prompt, user_prompt, config):
    """
    Uploads audio to Gemini and analyzes it.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env!")

    genai.configure(api_key=api_key)

    model_name = config['ai_settings'].get('model', 'gemini-1.5-flash')
    model = genai.GenerativeModel(model_name)

    # Upload file
    print(f"Uploading audio file {audio_path} to Gemini...")
    try:
        audio_file = genai.upload_file(audio_path)
    except Exception as e:
        return {
            "summary": f"Audio Upload failed: {e}",
            "keywords": []
        }

    instruction = (
        f"{system_prompt}\n"
        f"Specific instructions: {user_prompt}\n\n"
        f"Please provide the output in the following JSON format:\n"
        f"{{\n"
        f"  \"summary\": \"The summary of the video...\",\n"
        f"  \"keywords\": [\"keyword1\", \"keyword2\", ...]\n"
        f"}}\n\n"
        f"Analyze the attached audio file."
    )

    try:
        response = model.generate_content([instruction, audio_file])
        text_response = response.text

        # Simple cleanup
        if text_response.startswith("```json"):
            text_response = text_response.replace("```json", "", 1)
        elif text_response.startswith("```"):
            text_response = text_response.replace("```", "", 1)

        if text_response.endswith("```"):
            text_response = text_response.rsplit("```", 1)[0]

        return json.loads(text_response.strip())
    except Exception as e:
        print(f"AI Audio Analysis failed: {e}")
        return {
            "summary": f"AI Audio Analysis failed: {e}",
            "keywords": []
        }
