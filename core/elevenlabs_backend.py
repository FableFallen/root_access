# core/elevenlabs_backend.py

import os
import json
import urllib.request
import urllib.error
from typing import Optional
from core.config import GlobalConfig
# --- CHANGED IMPORT ---
from core.audio_models import AudioJob, AudioBackendBase 

class ElevenLabsBackend(AudioBackendBase):
    """
    Production backend interacting with ElevenLabs API.
    """
    def __init__(self, config: GlobalConfig):
        self.config = config
        self.base_url = "https://api.elevenlabs.io/v1/text-to-speech"

    def prepare(self, job: AudioJob, cache_path: Optional[str] = None) -> Optional[str]:
        if not self.config.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY not found.")
        if not cache_path:
            raise ValueError("ElevenLabsBackend requires a valid cache_path.")

        requested_voice = job.voice_id if job.voice_id else "default"
        
        if requested_voice not in self.config.ELEVENLABS_VOICES:
            print(f"[ElevenLabs] Aborting: Voice role '{requested_voice}' not defined in config.")
            return None

        voice_id = self.config.ELEVENLABS_VOICES[requested_voice]
        
        url = f"{self.base_url}/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.config.ELEVENLABS_API_KEY
        }
        
        payload = {
            "text": job.text,
            "model_id": self.config.ELEVENLABS_MODEL_ID,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            attempts = 2
            response_data = None
            
            for i in range(attempts):
                try:
                    with urllib.request.urlopen(req) as response:
                        if response.status == 200:
                            response_data = response.read()
                            break
                except urllib.error.HTTPError as e:
                    if i == attempts - 1: raise e
                    print(f"[ElevenLabs] Retry {i+1}/{attempts} failed: {e}")

            if response_data:
                with open(cache_path, "wb") as f:
                    f.write(response_data)
                return cache_path
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"API Error {e.code}: {error_body}")
        except Exception as e:
            raise Exception(f"Network Error: {e}")
            
        return None