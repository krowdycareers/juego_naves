"""Backend de audio basado en pygame.mixer."""

from __future__ import annotations

import math
from pathlib import Path
import random

import numpy as np

from ..core import config
from .sound_player import SystemSoundPlayer

try:
    import pygame
except ImportError:
    pygame = None


class PygameSoundPlayer:
    """Reproductor de sonido usando pygame.mixer con fallback seguro."""

    def __init__(self, pygame_module=None, fallback_player=None, asset_dir=None):
        self._pygame = pygame_module if pygame_module is not None else pygame
        self._fallback = fallback_player or SystemSoundPlayer()
        self._asset_dir = Path(asset_dir) if asset_dir is not None else config.SFX_DIR
        self._rng = random.Random()
        self._mixer = None
        self._shot_sounds = []
        self._enemy_hit_sounds = []
        self._friendly_hit_sounds = []
        self._collision_sounds = []
        self._ambience_sound = None
        self._ambience_channel = None
        self._shot_channel = None
        self._enemy_hit_channel = None
        self._friendly_hit_channel = None
        self._collision_channel = None
        self._ready = False
        self._initialize_mixer()

    def _initialize_mixer(self) -> None:
        if self._pygame is None:
            return

        try:
            mixer = self._pygame.mixer
            self._mixer = mixer
            if mixer.get_init() is None:
                mixer.init(frequency=44100, size=-16, channels=2)
            if hasattr(mixer, "set_num_channels"):
                mixer.set_num_channels(16)
            if hasattr(mixer, "Channel"):
                self._ambience_channel = mixer.Channel(0)
                self._shot_channel = mixer.Channel(1)
                self._enemy_hit_channel = mixer.Channel(2)
                self._friendly_hit_channel = mixer.Channel(3)
                self._collision_channel = mixer.Channel(4)

            self._shot_sounds = self._load_bank(
                "shot",
                lambda: self._build_weapon_shot_sound(
                    duration=0.14,
                    volume=0.55,
                ),
                variants=4,
            )
            self._enemy_hit_sounds = self._load_bank(
                "enemy_explosion",
                lambda: self._build_explosion_sound(
                    base_frequency=180,
                    duration=0.26,
                    volume=0.42,
                    brightness=0.25,
                ),
                variants=4,
            )
            self._friendly_hit_sounds = self._load_bank(
                "friendly_hit",
                lambda: self._build_laser_sound(
                    base_frequency=420,
                    sweep=160,
                    duration=0.18,
                    volume=0.22,
                    noise_level=0.01,
                ),
                variants=3,
            )
            self._collision_sounds = self._load_bank(
                "collision_explosion",
                lambda: self._build_explosion_sound(
                    base_frequency=120,
                    duration=0.32,
                    volume=0.34,
                    brightness=0.12,
                ),
                variants=3,
            )
            self._ambience_sound = self._load_single_asset(
                "ambience",
                lambda: self._build_ambience_sound(duration=4.5, volume=0.12),
            )
            self._ready = True
        except Exception:
            self._ready = False

    def _build_sound(self, waveform):
        stereo = np.column_stack((waveform, waveform))
        return self._pygame.sndarray.make_sound(stereo)

    def _build_laser_sound(
        self,
        base_frequency,
        sweep,
        duration=0.15,
        volume=0.3,
        noise_level=0.02,
    ):
        sample_rate = 44100
        sample_count = max(1, int(sample_rate * duration))
        timeline = np.linspace(0.0, duration, sample_count, endpoint=False, dtype=np.float32)
        progress = timeline / max(duration, 1e-6)
        envelope = (np.exp(-11.0 * timeline) * (1.0 - 0.15 * progress)).astype(np.float32)
        instantaneous_frequency = base_frequency + sweep * progress
        phase = np.cumsum((2.0 * math.pi * instantaneous_frequency) / sample_rate).astype(np.float32)
        body = np.sin(phase)
        harmonic = 0.55 * np.sin(phase * 1.98 + 0.3)
        click = 0.35 * np.sign(np.sin(phase * 2.6))
        noise = self._rng.uniform(-1.0, 1.0) * np.random.uniform(-1.0, 1.0, sample_count).astype(np.float32)
        mono = ((body + harmonic + click + noise_level * noise) * envelope * volume * 32767).astype(np.int16)
        return self._build_sound(mono)

    def _build_weapon_shot_sound(self, duration=0.14, volume=0.5):
        sample_rate = 44100
        sample_count = max(1, int(sample_rate * duration))
        timeline = np.linspace(0.0, duration, sample_count, endpoint=False, dtype=np.float32)
        noise = np.random.uniform(-1.0, 1.0, sample_count).astype(np.float32)

        click = noise * np.exp(-90.0 * timeline)

        pitch_drop = 210.0 - 120.0 * (timeline / max(duration, 1e-6))
        phase = np.cumsum((2.0 * math.pi * pitch_drop) / sample_rate).astype(np.float32)
        low_body = np.sin(phase) * np.exp(-26.0 * timeline)
        mids = np.sin(phase * 2.4 + 0.2) * np.exp(-38.0 * timeline) * 0.55
        crack = np.tanh(noise * 2.8) * np.exp(-42.0 * timeline) * 0.75
        tail = noise * np.exp(-18.0 * timeline) * 0.14

        mono = ((0.65 * click) + low_body + mids + crack + tail) * volume * 32767
        mono = mono.clip(-32767, 32767).astype(np.int16)
        return self._build_sound(mono)

    def _build_explosion_sound(self, base_frequency, duration=0.25, volume=0.35, brightness=0.2):
        sample_rate = 44100
        sample_count = max(1, int(sample_rate * duration))
        timeline = np.linspace(0.0, duration, sample_count, endpoint=False, dtype=np.float32)
        noise = np.random.uniform(-1.0, 1.0, sample_count).astype(np.float32)
        low_phase = np.cumsum(
            np.full(sample_count, (2.0 * math.pi * base_frequency) / sample_rate, dtype=np.float32)
        )
        sub = np.sin(low_phase)
        transient = np.exp(-18.0 * timeline).astype(np.float32)
        tail = np.exp(-4.5 * timeline).astype(np.float32)
        body = (noise * tail) + (sub * transient * 0.8) + (brightness * np.sin(low_phase * 2.3) * transient)
        mono = (body * volume * 32767).clip(-32767, 32767).astype(np.int16)
        return self._build_sound(mono)

    def _build_ambience_sound(self, duration=4.0, volume=0.12):
        sample_rate = 44100
        sample_count = max(1, int(sample_rate * duration))
        timeline = np.linspace(0.0, duration, sample_count, endpoint=False, dtype=np.float32)
        noise = np.random.uniform(-1.0, 1.0, sample_count).astype(np.float32)

        bpm = 138.0
        beat_phase = (timeline * bpm / 60.0) % 1.0
        bar_phase = (timeline * bpm / 240.0) % 1.0

        note_cycle = np.array([55.0, 73.4, 82.4, 73.4], dtype=np.float32)
        note_index = ((timeline * bpm / 60.0).astype(np.int32)) % len(note_cycle)
        bass_frequency = note_cycle[note_index]
        bass_phase = np.cumsum((2.0 * math.pi * bass_frequency) / sample_rate).astype(np.float32)

        kick_env = np.exp(-18.0 * beat_phase)
        offbeat_env = np.exp(-28.0 * ((beat_phase + 0.5) % 1.0))
        hat_env = np.exp(-90.0 * beat_phase) + 0.65 * np.exp(-90.0 * ((beat_phase + 0.5) % 1.0))

        bass = np.sin(bass_phase) * (0.35 + 0.65 * kick_env)
        sub = np.sin(bass_phase * 0.5 + 0.2) * kick_env * 0.55

        chord_frequency = 220.0 + 40.0 * np.sin(2.0 * math.pi * bar_phase)
        chord_phase = np.cumsum((2.0 * math.pi * chord_frequency) / sample_rate).astype(np.float32)
        synth = (
            np.sin(chord_phase)
            + 0.45 * np.sin(chord_phase * 1.5 + 0.6)
            + 0.20 * np.sin(chord_phase * 2.0 + 1.1)
        ) * (0.35 + 0.25 * np.sin(2.0 * math.pi * beat_phase))

        hats = np.tanh(noise * 3.2) * hat_env * 0.12
        snare = np.tanh(noise * 2.6) * offbeat_env * 0.18
        riser = np.sin(2.0 * math.pi * (310.0 + 35.0 * np.sin(2.0 * math.pi * bar_phase)) * timeline) * 0.04

        mono = (bass * 0.42) + (sub * 0.28) + (synth * 0.22) + hats + snare + riser
        mono = (mono * volume * 32767).clip(-32767, 32767).astype(np.int16)
        return self._build_sound(mono)

    def _load_bank(self, stem, generator, variants=3):
        bank = self._load_asset_bank(stem)
        if bank:
            return bank
        return [generator() for _ in range(max(1, variants))]

    def _load_asset_bank(self, stem):
        if self._pygame is None:
            return []

        sounds = []
        for path in self._iter_candidate_paths(stem):
            try:
                sounds.append(self._pygame.mixer.Sound(str(path)))
            except Exception:
                continue
        return sounds

    def _load_single_asset(self, stem, generator):
        bank = self._load_asset_bank(stem)
        if bank:
            return bank[0]
        return generator()

    def _iter_candidate_paths(self, stem):
        if not self._asset_dir.exists():
            return []

        candidates = []
        for extension in ("wav", "ogg"):
            direct = self._asset_dir / f"{stem}.{extension}"
            if direct.exists():
                candidates.append(direct)

            for indexed in sorted(self._asset_dir.glob(f"{stem}_*.{extension}")):
                candidates.append(indexed)

        return candidates

    def _play_from_bank(self, bank, channel=None):
        if not bank:
            return False

        sound = self._rng.choice(bank)
        if channel is not None:
            channel.play(sound)
            return True

        sound.play()
        return True

    def play_shot(self) -> None:
        if self._ready and self._play_from_bank(self._shot_sounds, channel=self._shot_channel):
            return
        self._fallback.play_shot()

    def play_target_hit(self, entity_type: str) -> None:
        if str(entity_type).lower() == "malo":
            self.play_enemy_destroyed()
            return
        self.play_friendly_hit()

    def play_enemy_destroyed(self) -> None:
        if self._ready and self._play_from_bank(
            self._enemy_hit_sounds,
            channel=self._enemy_hit_channel,
        ):
            return
        self._fallback.play_enemy_destroyed()

    def play_friendly_hit(self) -> None:
        if self._ready and self._play_from_bank(
            self._friendly_hit_sounds,
            channel=self._friendly_hit_channel,
        ):
            return
        self._fallback.play_friendly_hit()

    def play_collision(self) -> None:
        if self._ready and self._play_from_bank(self._collision_sounds, channel=self._collision_channel):
            return
        self._fallback.play_collision()

    def start_ambience(self) -> None:
        if not self._ready or self._ambience_sound is None:
            self._fallback.start_ambience()
            return

        if self._ambience_channel is not None and self._ambience_channel.get_busy():
            return

        if self._ambience_channel is not None:
            self._ambience_channel.play(self._ambience_sound, loops=-1)
            self._ambience_channel.set_volume(0.12)
            return

        self._ambience_channel = self._ambience_sound.play(loops=-1)
        if self._ambience_channel is not None:
            self._ambience_channel.set_volume(0.12)

    def stop_ambience(self) -> None:
        if self._ambience_channel is not None:
            self._ambience_channel.stop()
            self._ambience_channel = None
            return
        self._fallback.stop_ambience()
