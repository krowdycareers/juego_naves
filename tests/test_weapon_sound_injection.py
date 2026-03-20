#!/usr/bin/env python3
"""Tests para la inyeccion de audio en Weapon/GameEngine."""

from src.game.game_engine import GameEngine
from src.game.space_entity import SpaceEntity
from src.game.weapon import Weapon


class FakeSoundPlayer:
    """Captura llamadas de audio sin depender del sistema operativo."""

    def __init__(self):
        self.shot_calls = 0
        self.target_hits = []

    def play_shot(self):
        self.shot_calls += 1

    def play_target_hit(self, entity_type):
        self.target_hits.append(entity_type)


def test_weapon_uses_injected_sound_player():
    sound_player = FakeSoundPlayer()
    weapon = Weapon(sound_player=sound_player)

    weapon.reproducir_sonido()
    weapon.reproducir_sonido_objetivo("malo")

    assert sound_player.shot_calls == 1
    assert sound_player.target_hits == ["malo"]


def test_game_engine_uses_weapon_audio_backend_on_hit():
    sound_player = FakeSoundPlayer()
    weapon = Weapon(sound_player=sound_player)
    engine = GameEngine(800, 600, weapon=weapon)

    target = SpaceEntity(100, 120, 20, tipo="malo")
    engine.entities = [target]

    hit = engine.process_shot(100, 120)

    assert hit is True
    assert sound_player.target_hits == ["malo"]
