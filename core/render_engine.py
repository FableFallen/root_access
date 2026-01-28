# core/render_engine.py

import pygame
import math
import random
from core.config import GlobalConfig
from core.models import GameState, UIState

class RenderEngine:
    def __init__(self, config: GlobalConfig):
        self.config = config
        
        # 1. Font Setup
        font_preferences = ["consolas", "menlo", "couriernew", "courier", "monospace"]
        self.font_size = 22
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

        # Post-Processing Setup
        self.canvas = pygame.Surface((self.config.WIDTH, self.config.HEIGHT))
        self.scanline_surface = self._generate_scanlines()
        self.vignette_surface = self._generate_vignette()

        # NEW: The Phosphor Bed Background
        self.bg_surface = self._generate_background()
    
    def _generate_background(self) -> pygame.Surface:
        """
        Creates a 'Phosphor Bed' background.
        It fills the screen with the base color, then tiles a subtle noise texture
        to simulate the physical coating of a CRT monitor.
        """
        # 1. Base Surface
        bg = pygame.Surface((self.config.WIDTH, self.config.HEIGHT))
        bg.fill(self.config.COLORS["BACKGROUND"])
        
        # 2. Generate a small noise tile (Optimization: Don't do 1024x768 noise per frame)
        tile_size = 128
        noise_tile = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        
        # We manually poke random pixels. 
        # Since it's done once at startup, we can afford a nested loop on a small tile.
        noise_tile.lock()
        for y in range(tile_size):
            for x in range(tile_size):
                if random.random() > 0.5:
                    # Random white/grey grain
                    grain = random.randint(0, 50)
                    # Very low alpha
                    alpha = self.config.CRT_NOISE_ALPHA
                    noise_tile.set_at((x, y), (grain, grain, grain, alpha))
        noise_tile.unlock()
        
        # 3. Tile it across the screen
        for y in range(0, self.config.HEIGHT, tile_size):
            for x in range(0, self.config.WIDTH, tile_size):
                bg.blit(noise_tile, (x, y))
                
        return bg

    def _generate_scanlines(self) -> pygame.Surface:
        """Generates a transparent surface with horizontal black lines."""
        surf = pygame.Surface((self.config.WIDTH, self.config.HEIGHT), pygame.SRCALPHA)
        color = (0, 0, 0, self.config.CRT_SCANLINE_ALPHA)
        
        # Draw a line every 2nd pixel
        for y in range(0, self.config.HEIGHT, 2):
            pygame.draw.line(surf, color, (0, y), (self.config.WIDTH, y), 1)
        return surf

    def _generate_vignette(self) -> pygame.Surface:
        """
        Generates a high-quality radial gradient for the CRT vignette.
        Uses a math-based falloff on a downsampled surface to ensure smoothness
        without causing massive startup lag.
        """
        # 1. Create a lower-res texture to generate the gradient on.
        #    (Calculating 1024x768 pixels in Python is slow; 256x192 is instant)
        scale_factor = 4
        w, h = self.config.WIDTH // scale_factor, self.config.HEIGHT // scale_factor
        gradient_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        cx, cy = w // 2, h // 2
        # Max distance is roughly the distance to the corner
        max_dist = math.hypot(cx, cy)
        
        # 2. Iterate pixels on the small surface
        #    Locking the surface is faster for pixel manipulation
        gradient_surf.lock()
        
        for y in range(h):
            for x in range(w):
                # Calculate distance from center
                dist = math.hypot(x - cx, y - cy)
                
                # Normalize distance (0.0 at center, 1.0 at corner)
                norm_dist = dist / max_dist
                
                # Apply Curve: Power of 3 pushes the darkness to the corners,
                # leaving the center clear.
                # Adjust '3' to '2' for a darker screen, or '4' for clearer center.
                alpha = int(255 * (norm_dist ** 3))
                
                # Clamp alpha to vignette limit from config
                final_alpha = min(alpha, self.config.CRT_VIGNETTE_ALPHA)
                
                # Set pixel (Black with calculated alpha)
                if final_alpha > 0:
                    gradient_surf.set_at((x, y), (0, 0, 0, final_alpha))
                    
        gradient_surf.unlock()
        
        # 3. Scale up to full screen
        #    Smoothscale interpolates the pixels, creating a perfect fog.
        return pygame.transform.smoothscale(gradient_surf, (self.config.WIDTH, self.config.HEIGHT))

    def _render_history(self, surface: pygame.Surface, game_state: GameState, start_y: int, ui_state: UIState = None):
        # (Identical logic to Phase 2, but accepts 'surface' arg instead of 'screen')
        current_y = start_y
        
        visible_history = game_state.history
        offset = ui_state.scroll_offset if ui_state else 0
        
        if offset > 0:
            visible_history = game_state.history[:-offset]
            self._render_scroll_indicator(surface, current_y)

        for entry in reversed(visible_history):
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
                surface.blit(text_surf, (self.margin_x, current_y))
                current_y -= self.line_height
            
            current_y -= 4

    def _render_scroll_indicator(self, surface: pygame.Surface, y_pos: int):
        text = "-- HISTORY SCROLL ACTIVE --"
        surf = self.font.render(text, True, self.config.COLORS["GRAY"])
        rect = surf.get_rect(center=(self.config.WIDTH // 2, y_pos - 10))
        surface.blit(surf, rect)

    def render(self, screen: pygame.Surface, game_state: GameState, ui_state: UIState):
        """
        Main draw call.
        """
        # 1. Draw the Phosphor Bed (Instead of flat fill)
        self.canvas.blit(self.bg_surface, (0, 0))
        
        # 1. Render Scene to Intermediate Canvas
        # self.canvas.fill(self.config.COLORS["BACKGROUND"])

        # Input (Dynamic Height)
        prompt = "> "
        full_input_text = prompt + ui_state.input_buffer
        input_lines = self._wrap_text_pixel(full_input_text, self.max_width_px)
        
        input_block_height = len(input_lines) * self.line_height
        input_start_y = self.config.HEIGHT - self.margin_y - input_block_height
        
        self._render_input_block(self.canvas, input_lines, input_start_y, ui_state.cursor_visible)

        # History (Bottom-up)
        history_bottom_y = input_start_y - self.margin_y
        self._render_history(self.canvas, game_state, history_bottom_y, ui_state)
        
        # 2. Apply Post-Processing
        if self.config.CRT_ENABLED:
            if self.config.CRT_SCANLINES:
                self.canvas.blit(self.scanline_surface, (0, 0))
            if self.config.CRT_VIGNETTE:
                self.canvas.blit(self.vignette_surface, (0, 0))

        # 3. Final Blit to Screen
        screen.blit(self.canvas, (0, 0))

    def _render_input_block(self, surface: pygame.Surface, lines: list[str], start_y: int, cursor_visible: bool):
        color = self.config.COLORS["CRT_GREEN"]
        for i, line in enumerate(lines):
            y_pos = start_y + (i * self.line_height)
            text_surf = self.font.render(line, True, color)
            surface.blit(text_surf, (self.margin_x, y_pos))

            if cursor_visible and i == len(lines) - 1:
                cursor_x = self.margin_x + text_surf.get_width()
                cursor_rect = pygame.Rect(cursor_x, y_pos + 2, 10, self.line_height - 4)
                pygame.draw.rect(surface, color, cursor_rect)

    def _wrap_text_pixel(self, text: str, max_width: int) -> list[str]:
        # (Identical to Phase 1)
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