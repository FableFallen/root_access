# core/config.py

import os
from dataclasses import dataclass, field
from typing import Tuple, Dict

@dataclass(frozen=True)
class GlobalConfig:
    """
    Central configuration for ROOT ACCESS.
    """
    # Display
    WIDTH: int = 1024
    HEIGHT: int = 768
    FPS: int = 60
    
    # Colors (R, G, B)
    COLORS: Dict[str, Tuple[int, int, int]] = field(default_factory=lambda: {
        "CRT_BRIGHT": (100, 255, 100), # New: High-intensity green
        "CRT_GREEN": (0, 255, 0),      # Standard
        "CRT_DIM": (0, 100, 0),        # Narration/Background
        "BACKGROUND": (10, 10, 10),
        "BLACK": (0, 0, 0),
        "WHITE": (255, 255, 255),      # Voice/Info
        "ERROR": (255, 50, 50),        # Alerts
        "GRAY": (150, 150, 150)
    })

    # Channel Styles: Maps logical channel -> {Color Key, Prefix}
    CHANNEL_THEME: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "terminal":  {"color": "CRT_GREEN",  "prefix": ""},         # Standard output
        "system":    {"color": "CRT_BRIGHT", "prefix": "[SYS] "},   # High-level OS messages
        "error":     {"color": "ERROR",      "prefix": "[ERR] "},   # Critical failures
        "voice":     {"color": "WHITE",      "prefix": "[VOICE] "}, # Speech
        "narration": {"color": "CRT_DIM",    "prefix": ""},         # Descriptive text
        "info":      {"color": "GRAY",       "prefix": "[INFO] "},  # Silent help text
    })

    # System & Audio
    USE_MOCK_AUDIO: bool = False
    # Options: "mock", "elevenlabs", "local"
    AUDIO_BACKEND: str = "elevenlabs" 
    AUDIO_CACHE_DIR: str = "content/audio_cache"

    # NEW: SFX Directory
    SFX_DIR: str = "content/sfx"
    
    # Mixer Settings
    AUDIO_FREQ: int = 44100
    AUDIO_SIZE: int = -16
    AUDIO_CHANNELS: int = 2
    AUDIO_BUFFER: int = 512 # Low latency
    
    # ElevenLabs
    ELEVENLABS_API_KEY: str = os.environ.get("ELEVENLABS_API_KEY", "")
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"
    ELEVENLABS_VOICES: Dict[str, str] = field(default_factory=lambda: {
        # Fallback / System (Rachel)
        "default":  "6GKrdmoEjw0kaLwUsndp", 
        "system":   "6GKrdmoEjw0kaLwUsndp",
        
        # Narrator (Josh/Storyteller)
        "narrator": "8JVbfL6oEdmuxKn5DK2C",
    })

    MAX_HISTORY_LINES: int = 100
    CURSOR_BLINK_RATE_MS: int = 500