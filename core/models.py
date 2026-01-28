# core/models.py

from dataclasses import dataclass, field
import time
from typing import List, Dict, Any, Optional
from core.config import GlobalConfig

@dataclass
class LogEntry:
    """
    A single line of output in the terminal history.
    """
    text: str
    channel: str = "terminal"  # "terminal", "voice", "narration", "system", "error"
    timestamp: float = field(default_factory=time.time)
    style: Optional[str] = None  # Future: "dim", "bold", etc.

@dataclass
class UIState:
    """
    Pure UI/Presentation state. Resetting this does not affect narrative progress.
    """
    # Input field
    input_buffer: str = ""
    cursor_visible: bool = True
    cursor_timer_ms: int = 0
    
    # Typewriter Effect State
    typed_line_partial: str = ""  # The characters currently visible
    typewriter_active: bool = False
    target_text_full: str = ""    # The full line we are revealing
    typewriter_timer_ms: int = 0
    typewriter_index: int = 0

class GameState:
    """
    The World + Narrative State.
    Maintains the 'Truth' of the game session.
    """
    def __init__(self, config: GlobalConfig):
        self.config = config
        
        # Access Level
        self.tier: int = 0  # 0: Guest, 1: User, 2: Admin
        
        # World State (Flags)
        self.flags: Dict[str, Any] = {}
        
        # Operational Mode
        self.mode: str = "terminal"  # "cutscene", "terminal", "combat", "locked"
        
        # Narrative Progression
        self.current_scene_id: str = "boot"
        self.scene_cursor: int = 0
        
        # Output History
        self.history: List[LogEntry] = []

    def append_history(self, text: str, channel: str = "terminal", style: str = None):
        """
        Adds a log entry and adheres to the history truncation rule.
        """
        entry = LogEntry(text=text, channel=channel, style=style)
        self.history.append(entry)
        
        # Enforce truncation
        if len(self.history) > self.config.MAX_HISTORY_LINES:
            excess = len(self.history) - self.config.MAX_HISTORY_LINES
            self.history = self.history[excess:]

    def set_flag(self, key: str, value: Any):
        self.flags[key] = value

    def get_flag(self, key: str, default: Any = None) -> Any:
        return self.flags.get(key, default)