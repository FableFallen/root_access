# core/render_engine.py

import pygame
from core.config import GlobalConfig
from core.models import GameState, UIState

class RenderEngine:
    def __init__(self, config: GlobalConfig):
        self.config = config
        
        # 1. Font Setup (Fallback Strategy)
        font_preferences = ["consolas", "menlo", "couriernew", "courier", "monospace"]
        self.font_size = 18
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), self.font_size)
        
        available_fonts = pygame.font.get_fonts()
        for pref in font_preferences:
            if pref in available_fonts:
                self.font = pygame.font.SysFont(pref, self.font_size)
                break

        # 2. Metrics
        self.line_height = self.font.get_linesize()
        self.margin_x = 20
        self.margin_y = 20
        self.max_width_px = self.config.WIDTH - (self.margin_x * 2)

# core/render_engine.py

# ... (imports and init remain unchanged) ...

    def _render_history(self, screen: pygame.Surface, game_state: GameState, start_y: int, ui_state: UIState = None):
        """
        Iterates backwards through history, taking scroll_offset into account.
        """
        current_y = start_y
        
        # --- NEW: Apply Scroll Offset ---
        # If offset is 0, we see everything. 
        # If offset is 5, we slice off the last 5 entries (the newest ones).
        visible_history = game_state.history
        
        # ui_state is passed optionally to keep signature flexible, but we need it for scroll
        # Note: You need to update the call site in render() to pass ui_state!
        offset = ui_state.scroll_offset if ui_state else 0
        
        if offset > 0:
            visible_history = game_state.history[:-offset]
            
            # Optional: Visual indicator that we are scrolled up
            self._render_scroll_indicator(screen, current_y)

        # Walk backwards through the visible slice
        for entry in reversed(visible_history):
            # ... (Theme resolving and wrapping logic remains identical) ...
            theme = self.config.CHANNEL_THEME.get(entry.channel, self.config.CHANNEL_THEME["terminal"])
            color_key = theme["color"]
            prefix = theme["prefix"]
            
            full_text = prefix + entry.text
            color = self.config.COLORS.get(color_key, (255, 255, 255))

            wrapped_lines = self._wrap_text_pixel(full_text, self.max_width_px)
            
            for line in reversed(wrapped_lines):
                if current_y < self.margin_y:
                    return 

                text_surf = self.font.render(line, True, color)
                screen.blit(text_surf, (self.margin_x, current_y))
                current_y -= self.line_height
            
            current_y -= 4

    def _render_scroll_indicator(self, screen: pygame.Surface, y_pos: int):
        """Small visual hint that history is scrolled."""
        text = "-- HISTORY SCROLL ACTIVE --"
        surf = self.font.render(text, True, self.config.COLORS["GRAY"])
        rect = surf.get_rect(center=(self.config.WIDTH // 2, y_pos - 10))
        screen.blit(surf, rect)

    def render(self, screen: pygame.Surface, game_state: GameState, ui_state: UIState):
        """Main draw call."""
        screen.fill(self.config.COLORS["BACKGROUND"])

        # Input
        prompt = "> "
        full_input_text = prompt + ui_state.input_buffer
        input_lines = self._wrap_text_pixel(full_input_text, self.max_width_px)
        input_block_height = len(input_lines) * self.line_height
        input_start_y = self.config.HEIGHT - self.margin_y - input_block_height
        
        self._render_input_block(screen, input_lines, input_start_y, ui_state.cursor_visible)

        # History
        history_bottom_y = input_start_y - self.margin_y
        
        # PASS UI_STATE HERE
        self._render_history(screen, game_state, history_bottom_y, ui_state)

    def _render_input_block(self, screen: pygame.Surface, lines: list[str], start_y: int, cursor_visible: bool):
        color = self.config.COLORS["CRT_GREEN"]
        for i, line in enumerate(lines):
            y_pos = start_y + (i * self.line_height)
            text_surf = self.font.render(line, True, color)
            screen.blit(text_surf, (self.margin_x, y_pos))

            if cursor_visible and i == len(lines) - 1:
                cursor_x = self.margin_x + text_surf.get_width()
                cursor_rect = pygame.Rect(cursor_x, y_pos + 2, 10, self.line_height - 4)
                pygame.draw.rect(screen, color, cursor_rect)

    def _wrap_text_pixel(self, text: str, max_width: int) -> list[str]:
        """Identical to previous implementation"""
        if not text:
            return [""]
        words = text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            separator = " " if current_line else ""
            test_line = current_line + separator + word
            if self.font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                if self.font.size(word)[0] > max_width:
                    chars = list(word)
                    temp_str = ""
                    for char in chars:
                        if self.font.size(temp_str + char)[0] <= max_width:
                            temp_str += char
                        else:
                            lines.append(temp_str)
                            temp_str = char
                    current_line = temp_str
                else:
                    current_line = word
        if current_line:
            lines.append(current_line)
        return lines