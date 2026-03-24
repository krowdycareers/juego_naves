"""
GameEngine - Motor principal del juego.
Contiene la lógica de juego, colisiones, entidades y puntuación.
"""

import random
import math

from ..core import config
from .space_entity import SpaceEntity
from .weapon import Weapon


class GameEngine:
    """Motor del juego que maneja lógica, entidades y física."""

    def __init__(self, screen_width, screen_height, weapon=None):
        """
        Args:
            screen_width: Ancho de la pantalla
            screen_height: Altura de la pantalla
        """
        self.width = screen_width
        self.height = screen_height
        self.score = 0
        self.entities = []
        self.weapon = weapon or Weapon()
        
        self._initialize_entities()

    def _initialize_entities(self):
        """Crea e inicializa las entidades del juego."""
        self.entities = self._create_space_entities(
            config.NUM_ENTITIES,
            self.width,
            self.height,
            config.ENTITY_SIZE
        )

    def _create_space_entities(self, count, width, height, size):
        """Crea entidades espaciales sin colisiones entre ellas."""
        entities = []
        attempts_max = config.ENTITY_SPAWN_ATTEMPTS

        for _ in range(count):
            for _ in range(attempts_max):
                x = random.randint(0, max(0, width - size))
                y = random.randint(0, max(0, height - size))
                entity_type = random.choice(['bueno', 'malo'])

                new_entity = SpaceEntity(
                    x, y, size,
                    vx=10, vy=10,
                    tipo=entity_type
                )

                # Verificar colisión con existentes
                collision = any(
                    new_entity.detectar_colision(e, alto_total=height) for e in entities
                )

                if not collision:
                    entities.append(new_entity)
                    break

        return entities

    def update(self, game_frame, pointer=None):
        """
        Actualiza el estado del juego.
        
        Args:
            game_frame: Frame del juego (imagen)
            pointer: Posición del apuntador (x, y) o None para huida
        """
        HEIGHT, WIDTH = game_frame.shape[0:2]
        
        # 1. Actualizar explosiones y reapariciones
        for entity in self.entities:
            reaparecio = entity.actualizar_explosion_y_reaparicion()
            if reaparecio:
                entity.x = random.randint(0, max(0, WIDTH - entity.size))
                entity.y = random.randint(0, max(0, HEIGHT - entity.size))

        # 2. Detectar colisiones entre entidades
        self._handle_entity_collisions()

        # 3. Aplicar lógica de huida si hay apuntador
        if pointer is not None:
            self.make_entities_flee(pointer[0], pointer[1])

        # 4. Mover entidades
        for entity in self.entities:
            if entity.activo:
                entity.mover(WIDTH, HEIGHT)

    def _handle_entity_collisions(self):
        """Maneja colisiones entre entidades opuestas."""
        for i in range(len(self.entities)):
            for j in range(i + 1, len(self.entities)):
                a = self.entities[i]
                b = self.entities[j]

                if (not a.activo) or (not b.activo) or a.en_explosion or b.en_explosion:
                    continue

                misma_altura = abs(a.y - b.y) <= max(
                    8,
                    int((a.radio_colision(alto_total=self.height) + b.radio_colision(alto_total=self.height)) * config.COLLISION_HEIGHT_THRESHOLD)
                )
                opuestos = a.tipo != b.tipo

                # Si colisionan y están en la misma altura, explotan
                if opuestos and misma_altura and a.detectar_colision(b, alto_total=self.height):
                    self.weapon.reproducir_sonido_colision()
                    a.iniciar_explosion(
                        frames_explosion=config.COLLISION_EXPLOSION_FRAMES,
                        iteraciones_reaparicion=random.randint(
                            config.COLLISION_RESPAWN_ITERATIONS_MIN,
                            config.COLLISION_RESPAWN_ITERATIONS_MAX
                        )
                    )
                    b.iniciar_explosion(
                        frames_explosion=config.COLLISION_EXPLOSION_FRAMES,
                        iteraciones_reaparicion=random.randint(
                            config.COLLISION_RESPAWN_ITERATIONS_MIN,
                            config.COLLISION_RESPAWN_ITERATIONS_MAX
                        )
                    )
                    self.score -= 1
                    continue

                a.rebotar(b, alto_total=self.height)

    def make_entities_flee(self, pointer_x, pointer_y):
        """
        Hace que las naves enemigas huyan del apuntador.
        
        Args:
            pointer_x: Posición X del apuntador
            pointer_y: Posición Y del apuntador
        """
        for entity in self.entities:
            if not entity.activo or entity.en_explosion or entity.tipo != 'malo':
                continue

            dx = entity.x - pointer_x
            dy = entity.y - pointer_y
            dist = math.hypot(dx, dy)

            if dist < config.ENTITY_ESCAPE_DETECTION_RANGE:
                if dist > 1e-3:
                    ndx = dx / dist
                    ndy = dy / dist
                else:
                    ndx, ndy = 0.0, 0.0

                base_speed = max(
                    config.ENTITY_ESCAPE_BASE_SPEED_MIN,
                    min(
                        config.ENTITY_ESCAPE_BASE_SPEED_MAX,
                        config.ENTITY_ESCAPE_BASE_SPEED_MAX * (1.0 - dist / config.ENTITY_ESCAPE_DETECTION_RANGE)
                    )
                )
                target_vx = ndx * base_speed
                target_vy = ndy * base_speed

                blend = config.ENTITY_ESCAPE_VELOCITY_BLEND
                entity.vx = (1.0 - blend) * entity.vx + blend * target_vx
                entity.vy = (1.0 - blend) * entity.vy + blend * target_vy

    def process_shot(self, shot_x, shot_y):
        """
        Procesa un disparo.
        
        Args:
            shot_x: Posición X del disparo
            shot_y: Posición Y del disparo
            
        Returns:
            bool: Si acertó algún objetivo
        """
        for entity in self.entities:
            if not entity.activo or entity.en_explosion:
                continue

            if entity.contiene_punto_disparo(
                shot_x,
                shot_y,
                alto_total=self.height,
                padding=config.HITBOX_PADDING + config.WEAPON_RETICLE_HIT_PADDING,
            ):
                if entity.tipo == 'malo':
                    self.weapon.reproducir_sonido_muerte_enemigo()
                    self.score += config.SHOT_SCORE_ENEMY
                else:
                    self.weapon.reproducir_sonido_impacto_aliado()
                    self.score -= config.SHOT_SCORE_PENALTY_FRIENDLY

                entity.iniciar_explosion(
                    frames_explosion=config.COLLISION_EXPLOSION_FRAMES,
                    iteraciones_reaparicion=random.randint(
                        config.COLLISION_RESPAWN_ITERATIONS_MIN,
                        config.COLLISION_RESPAWN_ITERATIONS_MAX
                    )
                )
                return True

        return False

    def get_score(self):
        """Retorna la puntuación actual."""
        return int(self.score)
