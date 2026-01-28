# story/scene_validator.py

from typing import Dict, List, Any

class SceneValidationError(Exception):
    pass

class SceneValidator:
    """
    Enforces the JSON schema for Scenes.
    Prevents bad data from crashing the runtime.
    """
    
    REQUIRED_TOP_LEVEL = {"schema_version", "scene_id", "steps"}
    
    # Define required fields for each step type
    # (Optional fields like 'channel' or 'speed' are not listed here)
    STEP_REQUIREMENTS = {
        "print": ["text"],
        "typewrite": ["text"],
        "wait": ["seconds"],
        "voice": ["text"],        
        "require_command": ["commands"], # output_flag is optional
        "set_flag": ["key", "value"],
        "branch": ["if", "then"],
        "sfx": ["sfx_id"],

        # --- NEW RPG TYPES ---
        "give_item": ["item_id"],   # optional: qty
        "remove_item": ["item_id"], # optional: qty
        "quest_update": ["quest_id", "status"], # "active", "completed"
        "combat_start": ["enemy_name", "hp"],
        "combat_end": [] # No args required
    }

    def validate(self, data: Dict[str, Any]):
        """
        Raises SceneValidationError if data is invalid.
        """
        # 1. Top-Level Checks
        missing_keys = self.REQUIRED_TOP_LEVEL - data.keys()
        if missing_keys:
            raise SceneValidationError(f"Missing top-level keys: {missing_keys}")

        if data["schema_version"] != 1:
            raise SceneValidationError(f"Unsupported schema version: {data.get('schema_version')}")

        if not isinstance(data["steps"], list):
            raise SceneValidationError("'steps' must be a list.")

        # 2. Step-Level Checks
        for i, step in enumerate(data["steps"]):
            self._validate_step(step, i)

    def _validate_step(self, step: Dict[str, Any], index: int):
        # A. Check Type
        if "type" not in step:
            raise SceneValidationError(f"Step #{index} missing 'type'.")
        
        step_type = step["type"]
        if step_type not in self.STEP_REQUIREMENTS:
            raise SceneValidationError(f"Step #{index} has unknown type: '{step_type}'")

        # B. Check Required Fields
        required = self.STEP_REQUIREMENTS[step_type]
        for field in required:
            if field not in step:
                raise SceneValidationError(f"Step #{index} ({step_type}) missing required field: '{field}'")