#!/usr/bin/env python3
"""Tests para el backend de audio basado en pygame."""

from src.audio.pygame_sound_player import PygameSoundPlayer


class FakeFallbackPlayer:
    """Registra llamadas de fallback sin tocar audio real."""

    def __init__(self):
        self.shot_calls = 0
        self.target_hits = []
        self.collision_calls = 0
        self.ambience_starts = 0
        self.ambience_stops = 0

    def play_shot(self):
        self.shot_calls += 1

    def play_target_hit(self, entity_type):
        self.target_hits.append(entity_type)

    def play_collision(self):
        self.collision_calls += 1

    def start_ambience(self):
        self.ambience_starts += 1

    def stop_ambience(self):
        self.ambience_stops += 1


class FakeChannel:
    """Doble de canal devuelto por pygame.Sound.play."""

    def __init__(self):
        self.busy = True
        self.stop_calls = 0
        self.volume_values = []

    def get_busy(self):
        return self.busy

    def set_volume(self, value):
        self.volume_values.append(value)

    def stop(self):
        self.busy = False
        self.stop_calls += 1

    def play(self, sound, *args, **kwargs):
        self.busy = True
        return sound.play(*args, **kwargs)


class FakeSound:
    """Doble simple de pygame Sound."""

    def __init__(self):
        self.play_calls = 0
        self.play_kwargs = []
        self.channel = FakeChannel()

    def play(self, *args, **kwargs):
        self.play_calls += 1
        self.play_kwargs.append(kwargs)
        return self.channel


class FakeMixer:
    """Doble mínimo de pygame.mixer."""

    def __init__(self):
        self._initialized = None
        self.init_calls = 0
        self.channel_map = {}
        self.num_channels = 0

    def get_init(self):
        return self._initialized

    def init(self, frequency=44100, size=-16, channels=2):
        self._initialized = (frequency, size, channels)
        self.init_calls += 1

    def Sound(self, _path):
        return FakeSound()

    def set_num_channels(self, count):
        self.num_channels = count

    def Channel(self, index):
        if index not in self.channel_map:
            self.channel_map[index] = FakeChannel()
        return self.channel_map[index]


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
    player.play_collision()
    player.start_ambience()
    player.stop_ambience()

    assert fallback.shot_calls == 1
    assert fallback.target_hits == ["malo"]
    assert fallback.collision_calls == 1
    assert fallback.ambience_starts == 1
    assert fallback.ambience_stops == 1


def test_pygame_sound_player_builds_and_plays_generated_sounds():
    fake_pygame = FakePygame()
    fallback = FakeFallbackPlayer()
    player = PygameSoundPlayer(pygame_module=fake_pygame, fallback_player=fallback)

    player.play_shot()
    player.play_target_hit("malo")
    player.play_target_hit("bueno")
    player.play_collision()
    player.start_ambience()
    player.stop_ambience()

    assert fake_pygame.mixer.init_calls == 1
    assert len(fake_pygame.sndarray.created) == 15
    assert sum(sound.play_calls for sound in player._shot_sounds) == 1
    assert sum(sound.play_calls for sound in player._enemy_hit_sounds) == 1
    assert sum(sound.play_calls for sound in player._friendly_hit_sounds) == 1
    assert sum(sound.play_calls for sound in player._collision_sounds) == 1
    assert player._ambience_sound.play_calls == 1
    assert player._ambience_sound.channel.volume_values == [0.28]
    assert player._ambience_sound.channel.stop_calls == 1
    assert fallback.shot_calls == 0
    assert fallback.target_hits == []
    assert fallback.collision_calls == 0
    assert fallback.ambience_starts == 0
    assert fallback.ambience_stops == 0
