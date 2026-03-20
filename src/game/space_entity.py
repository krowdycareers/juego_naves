"""
SpaceEntity - Representa naves y astronautas en el juego.
Maneja movimiento, colisiones, explosiones y renderizado.
"""

import math

from ..core import config


class SpaceEntity:
    """
    Entidad espacial: nave o astronauta.
    
    Tipos:
    - 'malo': Nave enemiga (roja)
    - 'bueno': Astronauta amigo (azul)
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

    def detectar_colision(self, otro):
        """Detecta colisión real entre círculos usando distancia cuadrada (sin sqrt)."""
        if not self.activo or not otro.activo:
            return False
        # Optimización: usar distancia cuadrada para evitar sqrt innecesario
        dx = self.x - otro.x
        dy = self.y - otro.y
        dist_squared = dx * dx + dy * dy
        radio_sum = (self.size + otro.size) / 2
        radius_squared = radio_sum * radio_sum
        return dist_squared <= radius_squared

    def rebotar(self, otro):
        """Cambia la dirección en caso de colisión con otro cuadrado."""
        if self.detectar_colision(otro):
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
        Simula "profundidad" usando la altura (y) con escalones marcados:
        - arriba (y pequeña) -> más lejos -> más pequeño
        - abajo (y grande) -> más cerca -> más grande
        """
        h = max(1, int(alto_total))
        t = float(self.y) / float(h)
        t = max(0.0, min(1.0, t))

        # Cuantizar en 'steps' niveles (por ejemplo 4)
        if steps > 1:
            band = round(t * (steps - 1))
            t = band / float(steps - 1)

        # Suavizar un poco con curva cuadrática (más cambio al final)
        t = t * t

        return float(min_scale + (max_scale - min_scale) * t)

    def dibujar(self, img, escala=1.0):
        """Mantiene compatibilidad con el render OpenCV actual."""
        from ..rendering import OpenCVEntityRenderer

        renderer = OpenCVEntityRenderer()
        renderer.render_entity(self, img, escala=escala)
