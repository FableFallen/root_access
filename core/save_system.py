# core/save_system.py

import json
import os
from core.models import GameState

class SaveSystem:
    def __init__(self, save_dir: str = "content/saves"):
        self.save_dir = save_dir
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def save_game(self, game_state: GameState, slot_name: str = "save1") -> bool:
        """Writes GameState to JSON file."""
        data = game_state.to_dict()
        filepath = os.path.join(self.save_dir, f"{slot_name}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"[SaveSystem] Save Error: {e}")
            return False

    def load_game(self, game_state: GameState, slot_name: str = "save1") -> bool:
        """Reads JSON and restores GameState in-place."""
        filepath = os.path.join(self.save_dir, f"{slot_name}.json")
        if not os.path.exists(filepath):
            return False
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            game_state.restore_from_dict(data)
            return True
        except Exception as e:
            print(f"[SaveSystem] Load Error: {e}")
            return False