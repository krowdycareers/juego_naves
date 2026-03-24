"""
SpaceEntity - Representa naves humanas y alienigenas en el juego.
Maneja movimiento, colisiones, explosiones y renderizado.
"""

import math

from ..core import config


class SpaceEntity:
    """
    Entidad espacial: nave humana o alienigena.
    
    Tipos:
    - 'malo': Nave extraterrestre enemiga
    - 'bueno': Nave humana aliada
    """

    def __init__(self, x, y, size, vx=0, vy=0, tipo='bueno'):
        """Inicializa una entidad espacial."""
        self.x = x
        self.y = y
        self.size = size
        self.vx = vx
        self.vy = vy
        self.tipo = tipo
        self.color = (255, 0, 0) if tipo == 'bueno' else (0, 0, 255)
        self.activo = True
        self.iteraciones_para_reaparecer = 0
        self.en_explosion = False
        self.frames_explosion = 0
        self.frames_explosion_total = 0
        self.prox_iter_reaparicion = 0

    def ocultar(self, iteraciones=10):
        self.activo = False
        self.iteraciones_para_reaparecer = max(1, int(iteraciones))

    def actualizar_reaparicion(self):
        if self.activo:
            return False
        self.iteraciones_para_reaparecer -= 1
        if self.iteraciones_para_reaparecer <= 0:
            self.activo = True
            self.iteraciones_para_reaparecer = 0
            return True
        return False

    def mover(self, ancho, alto):
        """Mueve el cuadrado en base a su velocidad y rebota en los bordes del área rectangular."""
        if not self.activo or self.en_explosion:
            return
        self.x += self.vx
        self.y += self.vy

        # Rebote en bordes laterales
        if self.x < 0:
            self.x = 0  # Ajustar la posición dentro del área
            self.vx *= -1  # Invertir dirección en X
        elif self.x + self.size > ancho:
            self.x = ancho - self.size
            self.vx *= -1

        # Rebote en bordes superior e inferior
        if self.y < 0:
            self.y = 0
            self.vy *= -1  # Invertir dirección en Y
        elif self.y + self.size > alto:
            self.y = alto - self.size
            self.vy *= -1

    def detectar_colision(self, otro, alto_total=None):
        """Detecta colisión con una fase rápida por rect y una fina por círculo."""
        if not self.activo or not otro.activo:
            return False
        if not self.rect_colision(alto_total=alto_total).colliderect(otro.rect_colision(alto_total=alto_total)):
            return False
        dx = self.x - otro.x
        dy = self.y - otro.y
        dist_squared = dx * dx + dy * dy
        radio_sum = self.radio_colision(alto_total=alto_total) + otro.radio_colision(alto_total=alto_total)
        radius_squared = radio_sum * radio_sum
        return dist_squared <= radius_squared

    def radio_colision(self, alto_total=None, radius_factor=None):
        """Retorna un radio de colision mas cercano al tamano visible de la nave."""
        alto_referencia = max(1, int(alto_total if alto_total is not None else self.y + self.size))
        scale = self.escala_por_altura(
            alto_referencia,
            min_scale=config.DEPTH_MIN_SCALE,
            max_scale=config.DEPTH_MAX_SCALE,
            steps=config.DEPTH_STEPS,
        )
        factor = config.COLLISION_RADIUS_FACTOR if radius_factor is None else radius_factor
        return max(6.0, (self.size * 0.5) * scale * factor)

    def rect_colision(self, alto_total=None, padding=0):
        """Retorna un rectangulo visual aproximado para colisiones tipo sprite."""
        radius = self.radio_colision(alto_total=alto_total)
        if self.tipo == "malo":
            half_w = int(radius * 1.35 + padding)
            half_h = int(radius * 1.05 + padding)
        else:
            half_w = int(radius * 1.10 + padding)
            half_h = int(radius * 1.45 + padding)
        return Rect(
            int(self.x - half_w),
            int(self.y - half_h),
            max(1, half_w * 2),
            max(1, half_h * 2),
        )

    def contiene_punto_disparo(self, px, py, alto_total=None, padding=0):
        """Evalua si un disparo cae dentro del hitbox visible aproximado del sprite."""
        rect = self.rect_colision(alto_total=alto_total, padding=padding)
        if not rect.collidepoint(px, py):
            return False

        rx = max(1.0, rect.width / 2.0)
        ry = max(1.0, rect.height / 2.0)
        nx = (px - self.x) / rx
        ny = (py - self.y) / ry
        return (nx * nx) + (ny * ny) <= 1.0

    def rebotar(self, otro, alto_total=None):
        """Cambia la dirección en caso de colisión con otro cuadrado."""
        if self.detectar_colision(otro, alto_total=alto_total):
            if abs(self.x - otro.x) > abs(self.y - otro.y):
                self.vx *= -1  # Rebote en X
            else:
                self.vy *= -1  # Rebote en Y

    def iniciar_explosion(self, frames_explosion=10, iteraciones_reaparicion=10):
        self.en_explosion = True
        self.frames_explosion_total = max(1, int(frames_explosion))
        self.frames_explosion = self.frames_explosion_total
        self.prox_iter_reaparicion = max(1, int(iteraciones_reaparicion))

    def actualizar_explosion_y_reaparicion(self):
        # Actualizar fase de explosión si está activa
        if self.en_explosion:
            self.frames_explosion -= 1
            if self.frames_explosion <= 0:
                self.en_explosion = False
                # Tras la explosión, ocultar y comenzar cuenta para reaparecer
                self.ocultar(self.prox_iter_reaparicion or 10)
                self.prox_iter_reaparicion = 0
            return False

        # Si no está explotando, usar la lógica normal de reaparición
        return self.actualizar_reaparicion()

    def escala_por_altura(self, alto_total, min_scale=0.55, max_scale=1.35, steps=4):
        """
        Simula "profundidad" usando la altura (y) de forma suave:
        - arriba (y pequeña) -> más lejos -> más pequeño
        - abajo (y grande) -> más cerca -> más grande
        """
        h = max(1, int(alto_total))
        t = float(self.y) / float(h)
        t = max(0.0, min(1.0, t))

        if steps > 1:
            band = t * (steps - 1)
            lower = math.floor(band)
            upper = min(steps - 1, lower + 1)
            mix = band - lower
            t = ((lower / float(steps - 1)) * (1.0 - mix)) + ((upper / float(steps - 1)) * mix)

        # Curva suave tipo smootherstep para evitar saltos bruscos.
        t = t * t * (3.0 - 2.0 * t)

        return float(min_scale + (max_scale - min_scale) * t)


class Rect:
    """Rectangulo minimo para colisiones estilo sprite sin depender de pygame."""

    def __init__(self, x, y, width, height):
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.height

    def colliderect(self, other):
        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.bottom <= other.top
            or self.top >= other.bottom
        )

    def collidepoint(self, px, py):
        return self.left <= px <= self.right and self.top <= py <= self.bottom
