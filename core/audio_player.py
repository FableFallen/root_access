# core/audio_player.py

import pygame
import os
from core.config import GlobalConfig

class AudioPlayer:
    def __init__(self, config: GlobalConfig):
        self.config = config
        
        try:
            pygame.mixer.init(
                frequency=self.config.AUDIO_FREQ,
                size=self.config.AUDIO_SIZE,
                channels=self.config.AUDIO_CHANNELS,
                buffer=self.config.AUDIO_BUFFER
            )
            self.voice_channel = pygame.mixer.Channel(0)
            self.sfx_channel = pygame.mixer.Channel(1)
        except pygame.error as e:
            print(f"[AudioPlayer] Init Failed: {e}")
            self.voice_channel = None
            self.sfx_channel = None

    def play_voice(self, filepath: str):
        if not self.voice_channel: return
        if not os.path.exists(filepath): return
        try:
            sound = pygame.mixer.Sound(filepath)
            self.voice_channel.play(sound)
        except pygame.error as e:
            print(f"[AudioPlayer] Voice Error: {e}")

    # --- NEW METHOD ---
    def play_sfx(self, filepath: str):
        """Plays sound effect on secondary channel (mixes with voice)."""
        if not self.sfx_channel: return
        if not os.path.exists(filepath):
            print(f"[AudioPlayer] SFX File not found: {filepath}")
            return
            
        try:
            sound = pygame.mixer.Sound(filepath)
            self.sfx_channel.play(sound)
        except pygame.error as e:
            print(f"[AudioPlayer] SFX Error: {e}")

    def is_playing(self) -> bool:
        if self.voice_channel:
            return self.voice_channel.get_busy()
        return False
        
    def stop_all(self):
        if self.voice_channel: self.voice_channel.stop()
        if self.sfx_channel: self.sfx_channel.stop()