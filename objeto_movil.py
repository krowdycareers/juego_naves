import math
import time

import cv2
import numpy as np


class circulo:
    def __init__(self, x, y, size, vx=0, vy=0, tipo='bueno'):
        """Inicializa un cuadrado en movimiento."""
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

    def _dibujar_nave_roja(self, img, escala=1.0):
        cx, cy = int(self.x), int(self.y)
        body_w = max(46, int(72 * escala))
        body_h = max(18, int(24 * escala))
        dome_w = max(22, int(38 * escala))
        dome_h = max(14, int(22 * escala))
        blink_phase = time.time() * 8.0

        # Halo inferior suave para dar efecto de nave
        for i in range(3):
            alpha_h = 0.17 - (i * 0.05)
            halo = img.copy()
            cv2.ellipse(
                halo,
                (cx, cy + int(10 * escala)),
                (max(8, int((body_w * 0.38) + i * 6)), max(6, int((body_h * 0.35) + i * 5))),
                0,
                0,
                360,
                (0, 0, 120),
                -1,
                lineType=cv2.LINE_AA,
            )
            cv2.addWeighted(halo, max(0.0, alpha_h), img, 1.0 - max(0.0, alpha_h), 0, img)

        # Cuerpo principal
        cv2.ellipse(
            img,
            (cx, cy),
            (body_w // 2, body_h // 2),
            0,
            0,
            360,
            (20, 20, 170),
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx, cy + int(2 * escala)),
            (body_w // 2, max(5, int(body_h * 0.24))),
            0,
            0,
            180,
            (0, 0, 255),
            2,
            lineType=cv2.LINE_AA,
        )

        # Cúpula
        cv2.ellipse(
            img,
            (cx, cy - int(body_h * 0.45)),
            (dome_w // 2, dome_h // 2),
            0,
            180,
            360,
            (50, 80, 255),
            -1,
            lineType=cv2.LINE_AA,
        )

        # Ventanas
        win_count = 5
        for i in range(win_count):
            wx = int(cx - body_w * 0.3 + i * (body_w * 0.15))
            wy = int(cy - body_h * 0.12)
            cv2.circle(img, (wx, wy), max(2, int(3 * escala)), (180, 220, 255), -1, lineType=cv2.LINE_AA)

        # Luces del aro
        light_count = 8
        for i in range(light_count):
            t = (2 * math.pi / light_count) * i
            lx = int(cx + math.cos(t) * (body_w * 0.42))
            ly = int(cy + math.sin(t) * (body_h * 0.20))
            pulse = 0.45 + 0.55 * max(0.0, math.sin(blink_phase + i * 0.8))
            light_color = (
                int(120 + 110 * pulse),
                int(120 + 110 * pulse),
                int(200 + 55 * pulse),
            )
            if pulse > 0.8:
                glow = img.copy()
                cv2.circle(glow, (lx, ly), max(3, int(5 * escala)), light_color, -1, lineType=cv2.LINE_AA)
                cv2.addWeighted(glow, 0.18, img, 0.82, 0, img)
            cv2.circle(img, (lx, ly), max(1, int(2 * escala)), light_color, -1, lineType=cv2.LINE_AA)

    def _dibujar_astronauta_azul(self, img, escala=1.0):
        cx, cy = int(self.x), int(self.y)
        suit_white = (245, 242, 238)
        suit_shadow = (210, 205, 220)
        visor_dark = (35, 18, 70)
        visor_glow = (120, 80, 200)
        blue = (235, 170, 60)
        blue_dark = (200, 120, 35)
        gold = (60, 180, 245)

        # Sombra bajo el personaje para separarlo del fondo.
        shadow = img.copy()
        cv2.ellipse(
            shadow,
            (cx, cy + int(24 * escala)),
            (max(10, int(22 * escala)), max(4, int(6 * escala))),
            0,
            0,
            360,
            (120, 110, 160),
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.addWeighted(shadow, 0.25, img, 0.75, 0, img)

        # Mochila
        cv2.rectangle(
            img,
            (cx + int(10 * escala), cy - int(2 * escala)),
            (cx + int(20 * escala), cy + int(14 * escala)),
            suit_shadow,
            -1,
        )

        # Casco
        cv2.circle(img, (cx, cy - int(10 * escala)), max(14, int(18 * escala)), suit_white, -1, lineType=cv2.LINE_AA)
        cv2.ellipse(
            img,
            (cx - int(2 * escala), cy - int(10 * escala)),
            (max(10, int(12 * escala)), max(12, int(14 * escala))),
            -8,
            0,
            360,
            visor_dark,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx - int(7 * escala), cy - int(16 * escala)),
            (max(2, int(3 * escala)), max(4, int(5 * escala))),
            25,
            0,
            360,
            visor_glow,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx + int(1 * escala), cy - int(7 * escala)),
            (max(5, int(7 * escala)), max(3, int(4 * escala))),
            0,
            15,
            165,
            (235, 210, 255),
            max(1, int(2 * escala)),
            lineType=cv2.LINE_AA,
        )
        cv2.circle(img, (cx - int(4 * escala), cy - int(10 * escala)), max(1, int(1.6 * escala)), (235, 210, 255), -1, lineType=cv2.LINE_AA)
        cv2.circle(img, (cx + int(6 * escala), cy - int(10 * escala)), max(1, int(1.6 * escala)), (235, 210, 255), -1, lineType=cv2.LINE_AA)
        cv2.circle(img, (cx + int(14 * escala), cy - int(8 * escala)), max(3, int(4 * escala)), suit_shadow, -1, lineType=cv2.LINE_AA)

        # Torso
        cv2.ellipse(
            img,
            (cx, cy + int(10 * escala)),
            (max(12, int(16 * escala)), max(10, int(13 * escala))),
            -8,
            0,
            360,
            suit_white,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.rectangle(
            img,
            (cx - int(8 * escala), cy + int(7 * escala)),
            (cx + int(8 * escala), cy + int(12 * escala)),
            blue,
            -1,
        )
        cv2.rectangle(
            img,
            (cx - int(5 * escala), cy + int(4 * escala)),
            (cx + int(5 * escala), cy + int(11 * escala)),
            suit_shadow,
            -1,
        )
        cv2.circle(img, (cx - int(2 * escala), cy + int(8 * escala)), max(1, int(2 * escala)), (0, 0, 255), -1, lineType=cv2.LINE_AA)
        cv2.circle(img, (cx + int(2 * escala), cy + int(8 * escala)), max(1, int(2 * escala)), (0, 200, 0), -1, lineType=cv2.LINE_AA)

        # Brazos
        cv2.ellipse(img, (cx - int(16 * escala), cy + int(6 * escala)), (max(4, int(6 * escala)), max(7, int(9 * escala))), 40, 0, 360, suit_white, -1, lineType=cv2.LINE_AA)
        cv2.ellipse(img, (cx + int(16 * escala), cy + int(10 * escala)), (max(4, int(6 * escala)), max(7, int(9 * escala))), -35, 0, 360, suit_white, -1, lineType=cv2.LINE_AA)
        cv2.circle(img, (cx - int(24 * escala), cy + int(9 * escala)), max(4, int(5 * escala)), gold, -1, lineType=cv2.LINE_AA)
        cv2.circle(img, (cx + int(23 * escala), cy + int(14 * escala)), max(4, int(5 * escala)), gold, -1, lineType=cv2.LINE_AA)

        # Piernas
        cv2.ellipse(img, (cx - int(8 * escala), cy + int(26 * escala)), (max(5, int(7 * escala)), max(9, int(12 * escala))), 25, 0, 360, suit_white, -1, lineType=cv2.LINE_AA)
        cv2.ellipse(img, (cx + int(8 * escala), cy + int(24 * escala)), (max(5, int(7 * escala)), max(9, int(12 * escala))), -30, 0, 360, suit_white, -1, lineType=cv2.LINE_AA)
        cv2.ellipse(img, (cx - int(10 * escala), cy + int(30 * escala)), (max(5, int(7 * escala)), max(3, int(5 * escala))), 15, 0, 360, blue, -1, lineType=cv2.LINE_AA)
        cv2.ellipse(img, (cx + int(10 * escala), cy + int(28 * escala)), (max(5, int(7 * escala)), max(3, int(5 * escala))), -20, 0, 360, blue, -1, lineType=cv2.LINE_AA)
        cv2.ellipse(img, (cx - int(13 * escala), cy + int(38 * escala)), (max(5, int(7 * escala)), max(4, int(6 * escala))), 20, 0, 360, gold, -1, lineType=cv2.LINE_AA)
        cv2.ellipse(img, (cx + int(13 * escala), cy + int(35 * escala)), (max(5, int(7 * escala)), max(4, int(6 * escala))), -20, 0, 360, gold, -1, lineType=cv2.LINE_AA)

        # Acentos azules
        cv2.ellipse(img, (cx - int(12 * escala), cy + int(14 * escala)), (max(3, int(4 * escala)), max(3, int(5 * escala))), 35, 0, 360, blue_dark, 2, lineType=cv2.LINE_AA)
        cv2.ellipse(img, (cx + int(12 * escala), cy + int(18 * escala)), (max(3, int(4 * escala)), max(3, int(5 * escala))), -35, 0, 360, blue_dark, 2, lineType=cv2.LINE_AA)

    def _dibujar_explosion(self, img, escala=1.0):
        cx, cy = int(self.x), int(self.y)

        if self.frames_explosion_total <= 0:
            t = 0.0
        else:
            t = 1.0 - (self.frames_explosion / float(self.frames_explosion_total))
            t = max(0.0, min(1.0, t))

        max_radio = int(self.size * 2.0 * escala)
        radio = max(4, int(max_radio * (0.4 + 0.6 * t)))

        if self.tipo == 'malo':
            # Explosión de nave: anillo de choque + fragmentos metálicos
            ring_color = (0, 0, 255)
            inner_color = (0, 165, 255)

            # Anillo de choque
            ring_thickness = max(2, int(3 * (1.0 - t)))
            cv2.circle(img, (cx, cy), radio, ring_color, ring_thickness, lineType=cv2.LINE_AA)

            # Núcleo brillante
            inner_radio = max(3, int(radio * 0.3))
            cv2.circle(img, (cx, cy), inner_radio, inner_color, -1, lineType=cv2.LINE_AA)

            # Fragmentos: pequeños triángulos alrededor
            num_frag = 8
            for i in range(num_frag):
                angle = (2 * math.pi / num_frag) * i + t * 3.0
                dist = radio * (0.6 + 0.4 * t)
                fx = int(cx + math.cos(angle) * dist)
                fy = int(cy + math.sin(angle) * dist)
                dx = int(math.cos(angle) * 6)
                dy = int(math.sin(angle) * 6)
                pts = np.array(
                    [
                        [fx, fy],
                        [fx - dy, fy + dx],
                        [fx + dy, fy - dx],
                    ],
                    dtype=np.int32,
                )
                cv2.fillConvexPoly(img, pts, (200, 200, 255))
        else:
            # Explosión de astronauta: bola de fuego suave
            base_color = (255, 255, 255)
            inner_color = (255, 215, 0)

            # Capa exterior difusa
            halo = img.copy()
            cv2.circle(halo, (cx, cy), radio, base_color, -1, lineType=cv2.LINE_AA)
            alpha = 0.5 * (1.0 - t * 0.7)
            alpha = max(0.1, min(0.5, alpha))
            cv2.addWeighted(halo, alpha, img, 1.0 - alpha, 0, img)

            # Núcleo más brillante
            inner_radio = max(2, int(radio * 0.4))
            cv2.circle(img, (cx, cy), inner_radio, inner_color, -1, lineType=cv2.LINE_AA)

            # Pequeñas chispas alrededor
            num_sparks = 6
            for i in range(num_sparks):
                angle = (2 * math.pi / num_sparks) * i + t * 4.0
                dist = radio * (0.6 + 0.5 * t)
                sx = int(cx + math.cos(angle) * dist)
                sy = int(cy + math.sin(angle) * dist)
                cv2.circle(img, (sx, sy), 2, inner_color, -1, lineType=cv2.LINE_AA)

    def dibujar(self, img, escala=1.0):
        if not self.activo and not self.en_explosion:
            return
        if self.en_explosion:
            self._dibujar_explosion(img, escala)
        elif self.tipo == 'malo':
            self._dibujar_nave_roja(img, escala)
        else:
            self._dibujar_astronauta_azul(img, escala)
