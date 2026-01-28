# story/scene_types.py

from dataclasses import dataclass, field
from typing import List, Optional, Any

@dataclass
class Step:
    """
    A single instruction in a scene script.
    types: "print", "typewrite", "wait", "voice", "require_command", "set_flag"
    """
    type: str
    kwargs: dict = field(default_factory=dict)

@dataclass
class Scene:
    """
    A sequence of steps representing a narrative unit.
    """
    id: str
    steps: List[Step]