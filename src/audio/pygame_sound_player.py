"""Backend de audio basado en pygame.mixer."""

from __future__ import annotations

import math

import numpy as np

from .sound_player import SystemSoundPlayer

try:
    import pygame
except ImportError:
    pygame = None


class PygameSoundPlayer:
    """Reproductor de sonido usando pygame.mixer con fallback seguro."""

    def __init__(self, pygame_module=None, fallback_player=None):
        self._pygame = pygame_module if pygame_module is not None else pygame
        self._fallback = fallback_player or SystemSoundPlayer()
        self._shot_sound = None
        self._enemy_hit_sound = None
        self._friendly_hit_sound = None
        self._ready = False
        self._initialize_mixer()

    def _initialize_mixer(self) -> None:
        if self._pygame is None:
            return

        try:
            mixer = self._pygame.mixer
            if mixer.get_init() is None:
                mixer.init(frequency=44100, size=-16, channels=2)

            self._shot_sound = self._build_sound(880, duration=0.10, volume=0.35, decay=10.0)
            self._enemy_hit_sound = self._build_sound(520, duration=0.18, volume=0.40, decay=7.0)
            self._friendly_hit_sound = self._build_sound(260, duration=0.22, volume=0.28, decay=5.0)
            self._ready = True
        except Exception:
            self._ready = False

    def _build_sound(self, frequency, duration=0.15, volume=0.3, decay=8.0):
        sample_rate = 44100
        sample_count = max(1, int(sample_rate * duration))
        timeline = np.linspace(0.0, duration, sample_count, endpoint=False, dtype=np.float32)
        envelope = np.exp(-decay * timeline).astype(np.float32)
        wave = np.sin(2.0 * math.pi * frequency * timeline).astype(np.float32)
        mono = (wave * envelope * volume * 32767).astype(np.int16)
        stereo = np.column_stack((mono, mono))
        return self._pygame.sndarray.make_sound(stereo)

    def play_shot(self) -> None:
        if self._ready and self._shot_sound is not None:
            self._shot_sound.play()
            return
        self._fallback.play_shot()

    def play_target_hit(self, entity_type: str) -> None:
        if self._ready:
            if str(entity_type).lower() == "malo" and self._enemy_hit_sound is not None:
                self._enemy_hit_sound.play()
                return
            if str(entity_type).lower() != "malo" and self._friendly_hit_sound is not None:
                self._friendly_hit_sound.play()
                return

        self._fallback.play_target_hit(entity_type)
