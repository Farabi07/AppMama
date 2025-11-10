from datetime import datetime


def convert_to_24hr_format(time_str):
    try:
        time_str = time_str.strip().lower().replace(".", "")  # normalize "a.m." → "am"
        
        if "am" in time_str or "pm" in time_str:
            # Try parsing with hour + minute
            try:
                return datetime.strptime(time_str, "%I:%M %p").time()
            except ValueError:
                # Try parsing without minutes, e.g., "7 pm"
                return datetime.strptime(time_str, "%I %p").time()
        else:
            # Already 24-hour format
            return datetime.strptime(time_str, "%H:%M").time()
    except Exception:
        return None
    
from google.cloud import texttospeech
import base64

def synthesize_speech_neural2_female_base64(text):
    """Convert text to speech and return base64-encoded audio (no file storage)"""
    client = texttospeech.TextToSpeechClient()
    
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Neural2-F",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    
    # Return base64-encoded audio
    audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
    return audio_base64