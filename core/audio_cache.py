# core/audio_cache.py

import os
import hashlib
from core.config import GlobalConfig

class AudioCache:
    """
    Manages storage and retrieval of generated audio files.
    Key strategy: SHA256(backend + voice_id + text).
    """
    def __init__(self, config: GlobalConfig):
        self.config = config
        self.cache_dir = self.config.AUDIO_CACHE_DIR
        
        # Ensure directory exists
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def get_key(self, backend_name: str, job) -> str:
        """Generates a unique hash for a specific audio job."""
        # We combine all factors that change the audio output
        payload = f"{backend_name}|{job.voice_id}|{job.text}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def get_filepath(self, key: str) -> str:
        """Returns the full expected path for a cache key."""
        # Using .mp3 as generic container, though could be .wav depending on backend
        return os.path.join(self.cache_dir, f"{key}.mp3")

    def has(self, key: str) -> bool:
        """Checks if the file exists on disk."""
        path = self.get_filepath(key)
        return os.path.exists(path) and os.path.getsize(path) > 0