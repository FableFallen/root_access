# core/audio_models.py

import time
from dataclasses import dataclass, field
from typing import Optional, Any

@dataclass
class AudioJob:
    """A unit of work for the AudioEngine."""
    kind: str  # "tts", "pause", "sfx"
    text: Optional[str] = None
    seconds: float = 0.0
    voice_id: str = "default"
    
    # NEW: Identifier for Sound Effects
    sfx_id: Optional[str] = None
    
    data: Any = None 

@dataclass
class AudioEvent:
    """Feedback sent from Worker -> Main Thread."""
    type: str  # "STARTED", "FINISHED", "ERROR", "AUDIO_READY"
    job: AudioJob
    data: Any = None
    timestamp: float = field(default_factory=time.time)

class AudioBackendBase:
    """Interface for audio drivers."""
    def prepare(self, job: AudioJob, cache_path: Optional[str] = None) -> Optional[str]:
        raise NotImplementedError