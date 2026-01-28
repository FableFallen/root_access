# core/models.py

from dataclasses import dataclass, field
import time
from typing import List, Dict, Any, Optional
from core.config import GlobalConfig

@dataclass
class LogEntry:
    text: str
    channel: str = "terminal"
    timestamp: float = field(default_factory=time.time)
    style: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "channel": self.channel,
            "timestamp": self.timestamp,
            "style": self.style
        }

    @staticmethod
    def from_dict(data: dict) -> 'LogEntry':
        return LogEntry(
            text=data.get("text", ""),
            channel=data.get("channel", "terminal"),
            timestamp=data.get("timestamp", 0.0),
            style=data.get("style")
        )
@dataclass
class UIState:
    """
    Pure UI/Presentation state.
    """
    # Input field
    input_buffer: str = ""
    cursor_visible: bool = True
    cursor_timer_ms: int = 0
    
    # Typewriter Effect State
    typed_line_partial: str = ""
    typewriter_active: bool = False
    target_text_full: str = ""
    typewriter_timer_ms: int = 0
    typewriter_index: int = 0
    
    # --- NEW: Scroll & History ---
    scroll_offset: int = 0  # Number of LogEntries to skip from the bottom
    
    command_history: List[str] = field(default_factory=list)
    history_view_index: int = 0 # Tracks position in history while cycling

class GameState:
    def __init__(self, config: GlobalConfig):
        self.config = config
        self.tier: int = 0
        self.flags: Dict[str, Any] = {}
        self.mode: str = "terminal"
        self.current_scene_id: str = "boot_sequence"
        self.scene_cursor: int = 0
        self.history: List[LogEntry] = []

    def append_history(self, text: str, channel: str = "terminal", style: str = None):
        entry = LogEntry(text=text, channel=channel, style=style)
        self.history.append(entry)
        if len(self.history) > self.config.MAX_HISTORY_LINES:
            excess = len(self.history) - self.config.MAX_HISTORY_LINES
            self.history = self.history[excess:]

    def set_flag(self, key: str, value: Any):
        self.flags[key] = value

    def get_flag(self, key: str, default: Any = None) -> Any:
        return self.flags.get(key, default)

    def to_dict(self) -> dict:
        """Serialize critical state."""
        return {
            "tier": self.tier,
            "flags": self.flags,
            "mode": self.mode,
            "current_scene_id": self.current_scene_id,
            "scene_cursor": self.scene_cursor,
            # Persist the last 50 lines to keep save files small but providing context
            "history": [e.to_dict() for e in self.history[-50:]] 
        }

    def restore_from_dict(self, data: dict):
        """Update state in-place from loaded data."""
        self.tier = data.get("tier", 0)
        self.flags = data.get("flags", {})
        self.mode = data.get("mode", "terminal")
        self.current_scene_id = data.get("current_scene_id", "boot_sequence")
        self.scene_cursor = data.get("scene_cursor", 0)
        
        raw_history = data.get("history", [])
        self.history = [LogEntry.from_dict(item) for item in raw_history]