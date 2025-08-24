# ai/voice_recorder.py

import pyaudio
import wave
import tempfile
import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

class VoiceRecorder:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False

    def save_audio_to_file(self, audio_file):
        """Save the recorded audio to a temporary WAV file"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_filename = temp_file.name
        temp_file.close()

        # Write audio data to file (this is where you save the audio file)
        wf = wave.open(temp_filename, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(audio_file.read())
        wf.close()
        return temp_filename

    def transcribe_audio(self, audio_file_path):
        """Use OpenAI Whisper to transcribe audio to text"""
        try:
            with open(audio_file_path, 'rb') as audio_file:
                transcript = openai.Audio.transcribe(
                    model="whisper-1", file=audio_file, language="en"
                )
                return transcript['text']
        except Exception as e:
            return f"Error during transcription: {str(e)}"
        finally:
            # Clean up the temporary file
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)
