# story/scene_runner.py

from core.models import GameState, LogEntry
from core.audio_engine import AudioEngine, AudioJob
from story.scene_types import Scene
from story.story_loader import StoryLoader

class SceneRunner:
    def __init__(self, game_state: GameState, audio_engine: AudioEngine):
        self.game_state = game_state
        self.audio_engine = audio_engine
        self.loader = StoryLoader()
        
        self.current_scene: Scene = None
        self.current_step_index: int = 0
        
        # Step-specific state
        self.wait_timer: float = 0.0
        self.typewriter_timer: float = 0.0
        self.typewriter_char_index: int = 0
        self.current_log_entry: LogEntry = None 

    def load(self, scene_id: str):
        """Loads a new scene and resets cursors."""
        self.current_scene = self.loader.load_scene(scene_id)
        self.current_step_index = 0
        
        # SYNC: Update GameState immediately
        self.game_state.current_scene_id = scene_id
        self.game_state.scene_cursor = 0
        
        self._reset_step_state()

    def resume(self):
        """
        Reloads the scene defined in game_state and jumps to the stored cursor.
        Used after loading a save file.
        """
        scene_id = self.game_state.current_scene_id
        cursor = self.game_state.scene_cursor
        
        self.current_scene = self.loader.load_scene(scene_id)
        
        # Validate cursor range
        if self.current_scene and 0 <= cursor < len(self.current_scene.steps):
            self.current_step_index = cursor
        else:
            self.current_step_index = 0
            
        self._reset_step_state()

    def update(self, dt_ms: int, latest_command: str = None):
        if not self.current_scene or self.current_step_index >= len(self.current_scene.steps):
            return

        step = self.current_scene.steps[self.current_step_index]
        dt_seconds = dt_ms / 1000.0

        # --- EXISTING TYPES ---

        if step.type == "print":
            self.game_state.append_history(step.kwargs.get("text", ""), step.kwargs.get("channel", "terminal"))
            self._advance_step()

        elif step.type == "voice":
            text = step.kwargs.get("text", "")
            job = AudioJob(kind="tts", text=text)
            self.audio_engine.enqueue(job)
            self._advance_step()

        elif step.type == "wait":
            self.game_state.mode = "cutscene"
            self.wait_timer += dt_seconds
            if self.wait_timer >= step.kwargs.get("seconds", 1.0):
                self._advance_step()

        elif step.type == "typewrite":
            self.game_state.mode = "cutscene"
            
            full_text = step.kwargs.get("text", "")
            if self.current_log_entry is None:
                self.current_log_entry = LogEntry(text="", channel=step.kwargs.get("channel", "terminal"))
                self.game_state.history.append(self.current_log_entry)
            
            speed = step.kwargs.get("speed", 30)
            char_delay = 1.0 / speed
            
            self.typewriter_timer += dt_seconds
            
            if self.typewriter_char_index < len(full_text):
                while self.typewriter_timer >= char_delay:
                    self.typewriter_timer -= char_delay
                    if self.typewriter_char_index < len(full_text):
                        self.current_log_entry.text += full_text[self.typewriter_char_index]
                        self.typewriter_char_index += 1
                    else:
                        break
            
            if self.typewriter_char_index >= len(full_text):
                if self.typewriter_timer > 0.5: 
                    self._advance_step()

        elif step.type == "require_command":
            self.game_state.mode = "terminal"
            
            if latest_command:
                allowed = [c.lower() for c in step.kwargs.get("commands", [])]
                user_input = latest_command.lower().strip()
                
                if user_input in allowed:
                    # --- NEW LOGIC START ---
                    # If the script wants to remember WHAT was typed:
                    output_flag = step.kwargs.get("output_flag")
                    if output_flag:
                        self.game_state.set_flag(output_flag, user_input)
                    # --- NEW LOGIC END ---

                    self._advance_step()
                else:
                    fail_msg = step.kwargs.get("fail_msg")
                    if fail_msg:
                        self.game_state.append_history(fail_msg, "error")

        # --- NEW: LOGIC TYPES ---

        elif step.type == "set_flag":
            # Mutate State
            key = step.kwargs.get("key")
            val = step.kwargs.get("value")
            self.game_state.set_flag(key, val)
            self._advance_step()

        elif step.type == "branch":
            # Evaluate Condition
            condition_met = self._evaluate_condition(step.kwargs.get("if"))
            
            # Select Action Block
            action_block = step.kwargs.get("then") if condition_met else step.kwargs.get("else")
            
            if action_block:
                self._execute_branch_action(action_block)
            else:
                # If no 'else' block provided, just continue linear execution
                self._advance_step()

    def _evaluate_condition(self, condition: dict) -> bool:
        """Parses the 'if' block."""
        if not condition:
            return False
            
        if "flag_equals" in condition:
            key, target_val = condition["flag_equals"]
            current_val = self.game_state.get_flag(key)
            return current_val == target_val
            
        if "tier_at_least" in condition:
            target_tier = condition["tier_at_least"]
            return self.game_state.tier >= target_tier
            
        return False

    def _execute_branch_action(self, action: dict):
        """Executes 'goto_scene' or 'goto_step'."""
        if "goto_scene" in action:
            next_scene_id = action["goto_scene"]
            # append_history debug optional
            # self.game_state.append_history(f"[DEBUG] Jumping to scene: {next_scene_id}", "system")
            self.load(next_scene_id)
            
        elif "goto_step" in action:
            next_index = action["goto_step"]
            self.current_step_index = next_index
            self._reset_step_state()
            
        else:
            # No valid jump, just continue
            self._advance_step()

    def _advance_step(self):
        self.current_step_index += 1
        # SYNC: Update GameState whenever we move forward
        self.game_state.scene_cursor = self.current_step_index
        self._reset_step_state()

    def _reset_step_state(self):
        self.wait_timer = 0.0
        self.typewriter_timer = 0.0
        self.typewriter_char_index = 0
        self.current_log_entry = None