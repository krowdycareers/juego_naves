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
        self.collision_calls = 0
        self.ambience_starts = 0
        self.ambience_stops = 0
        self.enemy_destroyed_calls = 0
        self.friendly_hit_calls = 0

    def play_shot(self):
        self.shot_calls += 1

    def play_target_hit(self, entity_type):
        self.target_hits.append(entity_type)

    def play_collision(self):
        self.collision_calls += 1

    def play_enemy_destroyed(self):
        self.enemy_destroyed_calls += 1

    def play_friendly_hit(self):
        self.friendly_hit_calls += 1

    def start_ambience(self):
        self.ambience_starts += 1

    def stop_ambience(self):
        self.ambience_stops += 1


def test_weapon_uses_injected_sound_player():
    sound_player = FakeSoundPlayer()
    weapon = Weapon(sound_player=sound_player)

    weapon.reproducir_sonido()
    weapon.reproducir_sonido_objetivo("malo")
    weapon.reproducir_sonido_muerte_enemigo()
    weapon.reproducir_sonido_impacto_aliado()
    weapon.reproducir_sonido_colision()
    weapon.iniciar_ambiente()
    weapon.detener_ambiente()

    assert sound_player.shot_calls == 1
    assert sound_player.target_hits == ["malo"]
    assert sound_player.enemy_destroyed_calls == 1
    assert sound_player.friendly_hit_calls == 1
    assert sound_player.collision_calls == 1
    assert sound_player.ambience_starts == 1
    assert sound_player.ambience_stops == 1


def test_game_engine_uses_weapon_audio_backend_on_hit():
    sound_player = FakeSoundPlayer()
    weapon = Weapon(sound_player=sound_player)
    engine = GameEngine(800, 600, weapon=weapon)

    target = SpaceEntity(100, 120, 20, tipo="malo")
    engine.entities = [target]

    hit = engine.process_shot(100, 120)

    assert hit is True
    assert sound_player.enemy_destroyed_calls == 1


def test_game_engine_plays_collision_sound_on_entity_crash():
    sound_player = FakeSoundPlayer()
    weapon = Weapon(sound_player=sound_player)
    engine = GameEngine(800, 600, weapon=weapon)

    a = SpaceEntity(100, 100, 20, vx=0, vy=0, tipo="malo")
    b = SpaceEntity(100, 100, 20, vx=0, vy=0, tipo="bueno")
    engine.entities = [a, b]

    engine._handle_entity_collisions()

    assert sound_player.collision_calls == 1
