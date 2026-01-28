# main.py

import sys
import pygame
from core.config import GlobalConfig
from core.models import GameState, UIState
from core.input_engine import InputEngine
from core.render_engine import RenderEngine
from core.audio_engine import AudioEngine
from core.save_system import SaveSystem      # <--- NEW
from story.scene_runner import SceneRunner

def main():
    # 1. Setup
    pygame.init()
    config = GlobalConfig()
    screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
    pygame.display.set_caption("ROOT ACCESS")
    pygame.key.set_repeat(500, 50)
    clock = pygame.time.Clock()
    
    # 2. Instantiate Systems
    game_state = GameState(config)
    ui_state = UIState()
    input_engine = InputEngine(config)
    render_engine = RenderEngine(config)
    audio_engine = AudioEngine()
    save_system = SaveSystem()               # <--- NEW
    
    scene_runner = SceneRunner(game_state, audio_engine)
    scene_runner.load("main_menu")

    running = True
    
    while running:
        dt_ms = clock.tick(config.FPS)

        # Input
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
        
        command = input_engine.process_events(events, game_state, ui_state)
        input_engine.update(dt_ms, ui_state)
        
        if command:
            # Echo input
            game_state.append_history(f"> {command}", channel="terminal")
            
            # --- Meta Commands (Save/Load) ---
            cmd_lower = command.lower()
            
            if cmd_lower == "save":
                if save_system.save_game(game_state):
                    game_state.append_history("GAME SAVED [save1.json]", channel="system")
                else:
                    game_state.append_history("ERROR: SAVE FAILED", channel="error")
            
            elif cmd_lower == "load":
                if save_system.load_game(game_state):
                    # Resume SceneRunner logic from the loaded state
                    scene_runner.resume()
                    game_state.append_history("GAME LOADED [save1.json]", channel="system")
                else:
                    game_state.append_history("ERROR: NO SAVE FILE FOUND", channel="error")
                    
            elif cmd_lower in ["quit", "exit"]:
                running = False
            
            # --- Story Commands ---
            # Only pass to scene runner if we didn't just load/save/quit
            # (Though passing 'save' to runner is usually harmless if runner ignores it)
            scene_runner.update(dt_ms, latest_command=command)
        else:
            # Update Story (Continuously)
            scene_runner.update(dt_ms)

        # Audio & Render
        audio_engine.poll_events()
        render_engine.render(screen, game_state, ui_state)
        pygame.display.flip()

    audio_engine.shutdown()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()