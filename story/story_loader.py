# story/story_loader.py

import json
import os
from story.scene_types import Scene, Step
from story.scene_validator import SceneValidator, SceneValidationError # <--- NEW

class StoryLoader:
    def __init__(self, scenes_dir: str = "content/scenes"):
        self.scenes_dir = scenes_dir
        self.validator = SceneValidator() # <--- NEW

    def load_scene(self, scene_id: str) -> Scene:
        """
        Loads a scene from a JSON file in content/scenes/.
        Validates schema before parsing.
        """
        filename = f"{scene_id}.json"
        path = os.path.join(self.scenes_dir, filename)

        # 1. Check File Existence
        if not os.path.exists(path):
            return self._create_error_scene(scene_id, f"File not found: {path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 2. Validate Schema (New Step)
            self.validator.validate(data)
            
            # 3. Parse Data
            return self._parse_scene_data(data)

        except json.JSONDecodeError as e:
            return self._create_error_scene(scene_id, f"Invalid JSON: {e}")
        except SceneValidationError as e:
            return self._create_error_scene(scene_id, f"Schema Error: {e}")
        except Exception as e:
            return self._create_error_scene(scene_id, f"Unknown Error: {e}")

    def _create_error_scene(self, scene_id: str, error_msg: str) -> Scene:
        """
        Returns a fallback scene that displays the error in-game.
        """
        print(f"[StoryLoader] {error_msg}")
        return Scene(scene_id, [
            Step("print", {"text": "CRITICAL CONTENT ERROR", "channel": "error"}),
            Step("print", {"text": error_msg, "channel": "error"}),
            Step("voice", {"text": "System data corruption detected."})
        ])

    def _parse_scene_data(self, data: dict) -> Scene:
        scene_id = data.get("scene_id", "unknown")
        raw_steps = data.get("steps", [])
        
        parsed_steps = []
        for raw_step in raw_steps:
            step = self._parse_step(raw_step)
            if step:
                parsed_steps.append(step)
                
        return Scene(scene_id, parsed_steps)

    def _parse_step(self, raw_step: dict) -> Step:
        step_type = raw_step.get("type")
        if not step_type:
            return None
            
        kwargs = {k: v for k, v in raw_step.items() if k != "type"}
        return Step(type=step_type, kwargs=kwargs)