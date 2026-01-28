# core/input_engine.py

import pygame
from core.config import GlobalConfig
from core.models import GameState, UIState

class InputEngine:
    def __init__(self, config: GlobalConfig):
        self.config = config

    def process_events(self, events: list[pygame.event.Event], game_state: GameState, ui_state: UIState) -> str | None:
        
        # Lock input during cutscenes (except scrolling)
        input_allowed = game_state.mode in ["terminal", "combat"]
        command_to_return = None

        for event in events:
            # --- 1. Scrolling (Always allowed) ---
            if event.type == pygame.MOUSEWHEEL:
                ui_state.scroll_offset += event.y  # y is +1 (up) or -1 (down)
                self._clamp_scroll(ui_state, game_state)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_PAGEUP:
                    ui_state.scroll_offset += 5
                    self._clamp_scroll(ui_state, game_state)
                elif event.key == pygame.K_PAGEDOWN:
                    ui_state.scroll_offset -= 5
                    self._clamp_scroll(ui_state, game_state)
                
                # --- 2. Command History (Only if input allowed) ---
                elif input_allowed and event.key == pygame.K_UP:
                    self._cycle_history(ui_state, -1)
                elif input_allowed and event.key == pygame.K_DOWN:
                    self._cycle_history(ui_state, 1)

                # --- 3. Typing & Submission ---
                elif input_allowed:
                    command_to_return = self._handle_typing(event, ui_state)

        return command_to_return

    def update(self, dt_ms: int, ui_state: UIState):
        """Updates cursor blink timers."""
        ui_state.cursor_timer_ms += dt_ms
        if ui_state.cursor_timer_ms >= self.config.CURSOR_BLINK_RATE_MS:
            ui_state.cursor_timer_ms = 0
            ui_state.cursor_visible = not ui_state.cursor_visible

    def _clamp_scroll(self, ui_state: UIState, game_state: GameState):
        """Keeps scroll offset within valid bounds (0 to history length)."""
        max_scroll = max(0, len(game_state.history) - 1)
        ui_state.scroll_offset = max(0, min(ui_state.scroll_offset, max_scroll))

    def _cycle_history(self, ui_state: UIState, direction: int):
        """
        Cycles command history. 
        Direction: -1 (Older/Up), 1 (Newer/Down).
        """
        if not ui_state.command_history:
            return

        # Initialize index if we were at the "live" buffer
        if ui_state.history_view_index == -1:
             ui_state.history_view_index = len(ui_state.command_history)

        new_index = ui_state.history_view_index + direction
        
        # Clamp index
        # Range: 0 to len(history). 
        # len(history) represents the "blank" new line.
        new_index = max(0, min(new_index, len(ui_state.command_history)))

        ui_state.history_view_index = new_index

        if new_index == len(ui_state.command_history):
            ui_state.input_buffer = "" # Restored blank line
        else:
            ui_state.input_buffer = ui_state.command_history[new_index]

    def _handle_typing(self, event: pygame.event.Event, ui_state: UIState) -> str | None:
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            command = ui_state.input_buffer.strip()
            if command:
                # Add to history
                ui_state.command_history.append(command)
                # Reset view index to "end"
                ui_state.history_view_index = len(ui_state.command_history)
            
            ui_state.input_buffer = ""
            ui_state.scroll_offset = 0 # Snap on Send
            return command if command else None

        elif event.key == pygame.K_BACKSPACE:
            ui_state.input_buffer = ui_state.input_buffer[:-1]
            ui_state.scroll_offset = 0 # <--- NEW: Snap on Edit
        
        elif len(event.unicode) > 0 and event.unicode.isprintable():
            ui_state.input_buffer += event.unicode
            ui_state.scroll_offset = 0 # <--- NEW: Snap on Typing
            
        return None