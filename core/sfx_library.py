# core/sfx_library.py

import os
from core.config import GlobalConfig

class SFXLibrary:
    """
    Resolves SFX IDs to file paths.
    """
    def __init__(self, config: GlobalConfig):
        self.config = config
        
        # Ensure directory exists
        if not os.path.exists(self.config.SFX_DIR):
            os.makedirs(self.config.SFX_DIR)

        # Registry: Map logical ID -> filename
        self.registry = {
            "boot_hum": "boot_hum.wav",
            "alert": "alert.wav",
            "typing": "typing.wav",
            "glitch": "glitch.mp3"
        }

    def get_path(self, sfx_id: str) -> str | None:
        """Returns absolute path if file exists, else None."""
        if not sfx_id:
            return None
            
        filename = self.registry.get(sfx_id)
        if not filename:
            # Fallback: Check if sfx_id itself is a filename
            filename = sfx_id if "." in sfx_id else f"{sfx_id}.wav"
            
        path = os.path.join(self.config.SFX_DIR, filename)
        
        if os.path.exists(path):
            return path
        
        return None