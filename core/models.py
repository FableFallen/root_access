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
    
# --- NEW: Combat Models ---
@dataclass
class CombatState:
    active: bool = False
    enemy_name: str = ""
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    turn_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "active": self.active,
            "enemy_name": self.enemy_name,
            "enemy_hp": self.enemy_hp,
            "enemy_max_hp": self.enemy_max_hp,
            "turn_count": self.turn_count
        }
    
    def restore(self, data: dict):
        self.active = data.get("active", False)
        self.enemy_name = data.get("enemy_name", "")
        self.enemy_hp = data.get("enemy_hp", 0)
        self.enemy_max_hp = data.get("enemy_max_hp", 0)
        self.turn_count = data.get("turn_count", 0)

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

# --- GAME STATE ---
class GameState:
    def __init__(self, config: GlobalConfig):
        self.config = config
        
        # Core
        self.mode: str = "terminal" # "terminal", "cutscene", "combat"
        self.current_scene_id: str = "boot_sequence"
        self.scene_cursor: int = 0
        self.history: List[LogEntry] = []
        
        # RPG Stats (NEW)
        self.tier: int = 1
        self.hp: int = 20
        self.max_hp: int = 20
        self.flags: Dict[str, Any] = {}
        self.inventory: Dict[str, int] = {} # item_id -> quantity
        self.quests: Dict[str, str] = {}    # quest_id -> status ("active", "completed")
        
        self.combat: CombatState = CombatState()

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

    # --- Inventory Helpers ---
    def add_item(self, item_id: str, qty: int = 1):
        current = self.inventory.get(item_id, 0)
        self.inventory[item_id] = current + qty
        
    def remove_item(self, item_id: str, qty: int = 1) -> bool:
        current = self.inventory.get(item_id, 0)
        if current >= qty:
            self.inventory[item_id] = current - qty
            if self.inventory[item_id] <= 0:
                del self.inventory[item_id]
            return True
        return False
        
    def has_item(self, item_id: str, qty: int = 1) -> bool:
        return self.inventory.get(item_id, 0) >= qty

    # --- Persistence ---
    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "flags": self.flags,
            "inventory": self.inventory,
            "quests": self.quests,
            "mode": self.mode,
            "current_scene_id": self.current_scene_id,
            "scene_cursor": self.scene_cursor,
            "combat": self.combat.to_dict(),
            "history": [e.to_dict() for e in self.history[-50:]]
        }

    def restore_from_dict(self, data: dict):
        self.tier = data.get("tier", 1)
        self.hp = data.get("hp", 20)
        self.max_hp = data.get("max_hp", 20)
        self.flags = data.get("flags", {})
        self.inventory = data.get("inventory", {})
        self.quests = data.get("quests", {})
        self.mode = data.get("mode", "terminal")
        self.current_scene_id = data.get("current_scene_id", "boot_sequence")
        self.scene_cursor = data.get("scene_cursor", 0)
        
        if "combat" in data:
            self.combat.restore(data["combat"])
        
        raw_history = data.get("history", [])
        self.history = [LogEntry.from_dict(item) for item in raw_history]