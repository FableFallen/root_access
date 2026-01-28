# core/config.py

from dataclasses import dataclass, field
from typing import Tuple

@dataclass(frozen=True)
class GlobalConfig:
    """
    Central configuration for ROOT ACCESS.
    Constants are frozen to prevent accidental mutation during runtime.
    """
    # Display
    WIDTH: int = 1024
    HEIGHT: int = 768
    FPS: int = 60
    
    # Colors (R, G, B)
    COLORS: dict[str, Tuple[int, int, int]] = field(default_factory=lambda: {
        "CRT_GREEN": (0, 255, 0),
        "CRT_DIM": (0, 100, 0),
        "BACKGROUND": (10, 10, 10),
        "BLACK": (0, 0, 0),
        "WHITE": (255, 255, 255),
        "ERROR": (255, 50, 50)
    })

    # System
    USE_MOCK_AUDIO: bool = True
    MAX_HISTORY_LINES: int = 100  # Safety cap for scrollback buffer

    # Input
    CURSOR_BLINK_RATE_MS: int = 500