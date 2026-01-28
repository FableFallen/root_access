# main.py

import sys
import pygame
from core.config import GlobalConfig
from core.models import GameState, UIState
from core.input_engine import InputEngine
from core.render_engine import RenderEngine
from core.audio_engine import AudioEngine 
from core.audio_player import AudioPlayer # <--- NEW
from core.save_system import SaveSystem
from story.scene_runner import SceneRunner

def main():
    # 1. Setup
    pygame.init() # This inits display, font, etc.
    # Mixer is inited inside AudioPlayer to keep config centralized, 
    # but strictly called here on Main Thread.
    
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
    save_system = SaveSystem()
    
    # Audio Systems
    audio_player = AudioPlayer(config)    # <--- NEW (Main Thread)
    audio_engine = AudioEngine(config)    # <--- (Worker Thread)
    
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
            
            # Meta Commands
            cmd_lower = command.lower()
            if cmd_lower == "save":
                if save_system.save_game(game_state):
                    game_state.append_history("GAME SAVED [save1.json]", channel="system")
            elif cmd_lower == "load":
                if save_system.load_game(game_state):
                    scene_runner.resume()
                    game_state.append_history("GAME LOADED [save1.json]", channel="system")
            elif cmd_lower in ["quit", "exit"]:
                running = False
            
            # Story Update
            scene_runner.update(dt_ms, latest_command=command)
        else:
            scene_runner.update(dt_ms)

        # --- AUDIO PIPELINE ---
        audio_events = audio_engine.poll_events()
        for ae in audio_events:
            if ae.type == "AUDIO_READY":
                
                # Check Kind
                if ae.job.kind == "sfx":
                    audio_player.play_sfx(ae.data)
                else:
                    # Assume TTS
                    audio_player.play_voice(ae.data)
                
            elif ae.type == "ERROR":
                game_state.append_history(f"[Audio Error] {ae.data}", channel="error")

        # 2. Render
        render_engine.render(screen, game_state, ui_state)
        pygame.display.flip()

    audio_engine.shutdown()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()