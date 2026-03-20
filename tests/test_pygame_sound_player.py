#!/usr/bin/env python3
"""Tests para el backend de audio basado en pygame."""

from src.audio.pygame_sound_player import PygameSoundPlayer


class FakeFallbackPlayer:
    """Registra llamadas de fallback sin tocar audio real."""

    def __init__(self):
        self.shot_calls = 0
        self.target_hits = []

    def play_shot(self):
        self.shot_calls += 1

    def play_target_hit(self, entity_type):
        self.target_hits.append(entity_type)


class FakeSound:
    """Doble simple de pygame Sound."""

    def __init__(self):
        self.play_calls = 0

    def play(self):
        self.play_calls += 1


class FakeMixer:
    """Doble mínimo de pygame.mixer."""

    def __init__(self):
        self._initialized = None
        self.init_calls = 0

    def get_init(self):
        return self._initialized

    def init(self, frequency=44100, size=-16, channels=2):
        self._initialized = (frequency, size, channels)
        self.init_calls += 1


class FakeSndArray:
    """Doble mínimo de pygame.sndarray."""

    def __init__(self):
        self.created = []

    def make_sound(self, array):
        self.created.append(array)
        return FakeSound()


class FakePygame:
    """Doble de pygame suficiente para probar el player."""

    def __init__(self):
        self.mixer = FakeMixer()
        self.sndarray = FakeSndArray()


def test_pygame_sound_player_uses_fallback_when_pygame_is_missing():
    fallback = FakeFallbackPlayer()
    player = PygameSoundPlayer(pygame_module=None, fallback_player=fallback)

    player.play_shot()
    player.play_target_hit("malo")

    assert fallback.shot_calls == 1
    assert fallback.target_hits == ["malo"]


def test_pygame_sound_player_builds_and_plays_generated_sounds():
    fake_pygame = FakePygame()
    fallback = FakeFallbackPlayer()
    player = PygameSoundPlayer(pygame_module=fake_pygame, fallback_player=fallback)

    player.play_shot()
    player.play_target_hit("malo")
    player.play_target_hit("bueno")

    assert fake_pygame.mixer.init_calls == 1
    assert len(fake_pygame.sndarray.created) == 3
    assert player._shot_sound.play_calls == 1
    assert player._enemy_hit_sound.play_calls == 1
    assert player._friendly_hit_sound.play_calls == 1
    assert fallback.shot_calls == 0
    assert fallback.target_hits == []
