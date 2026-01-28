# story/scene_runner.py

import random
from core.models import GameState, LogEntry
from core.audio_engine import AudioEngine, AudioJob
from story.scene_types import Scene
from story.story_loader import StoryLoader

class SceneRunner:
    def __init__(self, game_state: GameState, audio_engine):
        self.game_state = game_state
        self.audio_engine = audio_engine
        self.loader = StoryLoader()
        
        self.current_scene: Scene = None
        self.current_step_index: int = 0
        
        # Step-specific timers
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
        # 1. COMBAT INTERCEPTION
        if self.game_state.mode == "combat":
            if latest_command:
                self._handle_combat_turn(latest_command)
            return  # Stop scene processing while in combat

        # 2. NORMAL SCENE PROCESSING
        if not self.current_scene or self.current_step_index >= len(self.current_scene.steps):
            return

        step = self.current_scene.steps[self.current_step_index]
        dt_seconds = dt_ms / 1000.0

        if step.type == "print":
            self.game_state.append_history(step.kwargs.get("text", ""), step.kwargs.get("channel", "terminal"))
            self._advance_step()

        elif step.type == "voice":
            text = step.kwargs.get("text", "")
            vid = step.kwargs.get("voice_id", "default")
            job = AudioJob(kind="tts", text=text, voice_id=vid)
            self.audio_engine.enqueue(job)
            self._advance_step()

        elif step.type == "sfx":
            sfx_id = step.kwargs.get("sfx_id")
            self.audio_engine.enqueue(AudioJob(kind="sfx", sfx_id=sfx_id))
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
                    out_flag = step.kwargs.get("output_flag")
                    if out_flag:
                        self.game_state.set_flag(out_flag, user_input)
                    self._advance_step()
                else:
                    fail_msg = step.kwargs.get("fail_msg")
                    if fail_msg:
                        self.game_state.append_history(fail_msg, "error")

        elif step.type == "set_flag":
            self.game_state.set_flag(step.kwargs.get("key"), step.kwargs.get("value"))
            self._advance_step()

        elif step.type == "branch":
            if self._evaluate_condition(step.kwargs.get("if")):
                self._execute_branch_action(step.kwargs.get("then"))
            else:
                self._execute_branch_action(step.kwargs.get("else"))

        # --- NEW RPG STEPS ---

        elif step.type == "give_item":
            item = step.kwargs.get("item_id")
            qty = step.kwargs.get("qty", 1)
            self.game_state.add_item(item, qty)
            self.game_state.append_history(f"[ITEM ACQUIRED: {item.upper()} x{qty}]", "system")
            self._advance_step()

        elif step.type == "remove_item":
            item = step.kwargs.get("item_id")
            qty = step.kwargs.get("qty", 1)
            if self.game_state.remove_item(item, qty):
                self.game_state.append_history(f"[ITEM LOST: {item.upper()} x{qty}]", "system")
            self._advance_step()

        elif step.type == "quest_update":
            qid = step.kwargs.get("quest_id")
            status = step.kwargs.get("status")
            self.game_state.quests[qid] = status
            self.game_state.append_history(f"[QUEST UPDATE: {qid.upper()} -> {status.upper()}]", "system")
            self._advance_step()

        elif step.type == "combat_start":
            enemy = step.kwargs.get("enemy_name", "Unknown Threat")
            hp = step.kwargs.get("hp", 20)
            
            self.game_state.combat.active = True
            self.game_state.combat.enemy_name = enemy
            self.game_state.combat.enemy_hp = hp
            self.game_state.combat.enemy_max_hp = hp
            self.game_state.combat.turn_count = 0
            
            self.game_state.mode = "combat"
            
            self.game_state.append_history(f"WARNING: {enemy.upper()} ENGAGED.", "error")
            self.game_state.append_history("COMBAT MODE INITIATED.", "system")
            self.game_state.append_history("COMMANDS: [ATTACK] [HEAL] [SCAN] [FLEE]", "terminal")
            self._advance_step()

# --- HELPER LOGIC ---

    def _evaluate_condition(self, condition: dict) -> bool:
        if not condition: return False
        if "flag_equals" in condition:
            key, val = condition["flag_equals"]
            return self.game_state.get_flag(key) == val
        if "has_item" in condition:
            item = condition["has_item"]
            return self.game_state.has_item(item)
        return False

    def _execute_branch_action(self, action: dict):
        if not action:
            self._advance_step()
            return
            
        if "goto_scene" in action:
            self.load(action["goto_scene"])
        elif "goto_step" in action:
            self.current_step_index = action["goto_step"]
            self.game_state.scene_cursor = self.current_step_index # Sync
            self._reset_step_state()
        else:
            self._advance_step()

    def _advance_step(self):
        self.current_step_index += 1
        self.game_state.scene_cursor = self.current_step_index
        self._reset_step_state()

    def _reset_step_state(self):
        self.wait_timer = 0.0
        self.typewriter_timer = 0.0
        self.typewriter_char_index = 0
        self.current_log_entry = None

# --- COMBAT LOGIC ---
    
    def _handle_combat_turn(self, command: str):
        cmd = command.lower().strip()
        cs = self.game_state.combat
        
        # Player Turn
        if cmd == "attack":
            dmg = random.randint(3, 8)
            cs.enemy_hp -= dmg
            self.game_state.append_history(f"> You attack for {dmg} DMG.", "terminal")
        elif cmd == "heal":
            amt = 5
            self.game_state.hp = min(self.game_state.max_hp, self.game_state.hp + amt)
            self.game_state.append_history(f"> Systems repaired (+{amt} HP).", "system")
        elif cmd == "scan":
            self.game_state.append_history(f"TARGET: {cs.enemy_name} | HP: {cs.enemy_hp}/{cs.enemy_max_hp}", "info")
            return # Scan doesn't cost a turn? Or maybe it does. Let's say it does.
        elif cmd == "flee":
            if random.random() > 0.5:
                self.game_state.append_history("ESCAPED SUCCESSFULLY.", "system")
                self._end_combat()
                return
            else:
                self.game_state.append_history("ESCAPE FAILED.", "error")
        else:
            self.game_state.append_history("Invalid Combat Command.", "error")
            return

        # Check Win
        if cs.enemy_hp <= 0:
            self.game_state.append_history(f"TARGET {cs.enemy_name} DESTROYED.", "system")
            self._end_combat()
            return

        # Enemy Turn
        enemy_dmg = random.randint(2, 6)
        self.game_state.hp -= enemy_dmg
        self.game_state.append_history(f"WARNING: Hull breach! Took {enemy_dmg} DMG. (Integrity: {self.game_state.hp})", "error")

        # Check Loss
        if self.game_state.hp <= 0:
            self.game_state.append_history("CRITICAL FAILURE. SYSTEM TERMINATED.", "error")
            self.game_state.mode = "cutscene" 
            # In a real game, trigger Game Over scene here
            # self.load("game_over") 

    def _end_combat(self):
        self.game_state.combat.active = False
        self.game_state.mode = "terminal" # Return to normal script flow
        # The runner will pick up the NEXT step in the JSON on the next update