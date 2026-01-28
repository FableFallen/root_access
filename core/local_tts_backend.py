# core/local_tts_backend.py

import os
from typing import Optional
from core.config import GlobalConfig
from core.audio_models import AudioJob, AudioBackendBase

# Try importing pyttsx3, handle missing dependency gracefully
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False

class LocalTTSBackend(AudioBackendBase):
    """
    Offline TTS using pyttsx3.
    Generates audio files locally without network calls.
    """
    def __init__(self, config: GlobalConfig):
        self.config = config
        if not HAS_PYTTSX3:
            print("[LocalTTS] Warning: pyttsx3 not installed. Audio generation will fail.")

    def prepare(self, job: AudioJob, cache_path: Optional[str] = None) -> Optional[str]:
        if not HAS_PYTTSX3:
            print("[LocalTTS] Error: pyttsx3 missing. Install via 'pip install pyttsx3'")
            return None
            
        if not cache_path:
            raise ValueError("LocalTTSBackend requires a valid cache_path.")

        try:
            # Initialize engine inside the worker thread to avoid thread affinity issues
            engine = pyttsx3.init()
            
            # Optional: Configure voice based on job.voice_id
            # This is highly system-dependent, so we stick to defaults for stability
            # voices = engine.getProperty('voices')
            # ... selection logic could go here ...

            # Save to file
            # pyttsx3 usually saves as .wav. If cache_path ends in .mp3, 
            # Pygame usually plays it anyway because it sniffs headers.
            engine.save_to_file(job.text, cache_path)
            engine.runAndWait()
            
            # Verify file creation
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
                return cache_path
            else:
                print("[LocalTTS] File generation failed (empty or missing).")
                return None

        except Exception as e:
            print(f"[LocalTTS] Generation Error: {e}")
            return None