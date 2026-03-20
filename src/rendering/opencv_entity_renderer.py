"""Renderizado OpenCV para entidades del juego."""

from __future__ import annotations

import math
import time

import cv2
import numpy as np


class OpenCVEntityRenderer:
    """Dibuja entidades del juego sobre frames de OpenCV."""

    def render_entities(self, entities, game_frame, height=None):
        """Dibuja una lista de entidades activas."""
        if height is None:
            height = game_frame.shape[0]

        for entity in entities:
            if not entity.activo and not entity.en_explosion:
                continue

            escala_base = 0.85 if entity.tipo == "malo" else 0.9
            escala = escala_base * entity.escala_por_altura(height)
            self.render_entity(entity, game_frame, escala=escala)

        return game_frame

    def render_entity(self, entity, img, escala=1.0):
        """Dibuja una sola entidad."""
        if not entity.activo and not entity.en_explosion:
            return
        if entity.en_explosion:
            self._draw_explosion(entity, img, escala)
        elif entity.tipo == "malo":
            self._draw_enemy_ship(entity, img, escala)
        else:
            self._draw_friendly_astronaut(entity, img, escala)

    def _draw_enemy_ship(self, entity, img, escala=1.0):
        cx, cy = int(entity.x), int(entity.y)
        body_w = max(46, int(72 * escala))
        body_h = max(18, int(24 * escala))
        dome_w = max(22, int(38 * escala))
        dome_h = max(14, int(22 * escala))
        blink_phase = time.time() * 8.0

        if escala < 0.7:
            for i in range(3):
                alpha = 0.18 - i * 0.05
                smoke = img.copy()
                cv2.circle(
                    smoke,
                    (cx, cy + int(body_h * 0.7)),
                    int(body_w * (0.25 + 0.12 * i)),
                    (120, 120, 120),
                    -1,
                    cv2.LINE_AA,
                )
                cv2.addWeighted(smoke, alpha, img, 1.0 - alpha, 0, img)

        for i in range(3):
            alpha_h = 0.17 - (i * 0.05)
            halo = img.copy()
            cv2.ellipse(
                halo,
                (cx, cy + int(10 * escala)),
                (
                    max(8, int((body_w * 0.38) + i * 6)),
                    max(6, int((body_h * 0.35) + i * 5)),
                ),
                0,
                0,
                360,
                (0, 0, 120),
                -1,
                lineType=cv2.LINE_AA,
            )
            cv2.addWeighted(halo, max(0.0, alpha_h), img, 1.0 - max(0.0, alpha_h), 0, img)

        for i in range(body_h):
            color = (20 + i, 20 + i, 170 + i // 2)
            cv2.ellipse(
                img,
                (cx, cy),
                (body_w // 2, body_h // 2 - i // 2),
                0,
                0,
                360,
                color,
                1,
                cv2.LINE_AA,
            )
        cv2.ellipse(img, (cx, cy), (body_w // 2, body_h // 2), 0, 0, 360, (40, 40, 200), -1, cv2.LINE_AA)
        cv2.ellipse(
            img,
            (cx, cy + int(2 * escala)),
            (body_w // 2, max(5, int(body_h * 0.24))),
            0,
            0,
            180,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.ellipse(
            img,
            (cx, cy - int(body_h * 0.45)),
            (dome_w // 2, dome_h // 2),
            0,
            180,
            360,
            (80, 120, 255),
            -1,
            cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx, cy - int(body_h * 0.45)),
            (dome_w // 2, dome_h // 2),
            0,
            180,
            360,
            (50, 80, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx - int(dome_w * 0.2), cy - int(body_h * 0.55)),
            (int(dome_w * 0.18), int(dome_h * 0.18)),
            0,
            0,
            360,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        for i in range(5):
            wx = int(cx - body_w * 0.3 + i * (body_w * 0.15))
            wy = int(cy - body_h * 0.12)
            cv2.circle(img, (wx, wy), max(2, int(3 * escala)), (180, 220, 255), -1, cv2.LINE_AA)

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
                cv2.circle(glow, (lx, ly), max(3, int(5 * escala)), light_color, -1, cv2.LINE_AA)
                cv2.addWeighted(glow, 0.18, img, 0.82, 0, img)
            cv2.circle(img, (lx, ly), max(1, int(2 * escala)), light_color, -1, cv2.LINE_AA)

    def _draw_friendly_astronaut(self, entity, img, escala=1.0):
        cx, cy = int(entity.x), int(entity.y)
        suit_white = (245, 242, 238)
        suit_shadow = (210, 205, 220)
        visor_dark = (35, 18, 70)
        visor_glow = (120, 80, 200)
        blue = (235, 170, 60)
        blue_dark = (200, 120, 35)
        gold = (60, 180, 245)

        if escala < 0.7:
            for i in range(3):
                alpha = 0.18 - i * 0.05
                smoke = img.copy()
                cv2.circle(
                    smoke,
                    (cx, cy + int(18 * escala)),
                    int(12 * escala + 6 * i),
                    (120, 120, 120),
                    -1,
                    cv2.LINE_AA,
                )
                cv2.addWeighted(smoke, alpha, img, 1.0 - alpha, 0, img)

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

        cv2.rectangle(
            img,
            (cx + int(10 * escala), cy - int(2 * escala)),
            (cx + int(20 * escala), cy + int(14 * escala)),
            suit_shadow,
            -1,
        )
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
        cv2.rectangle(img, (cx - int(8 * escala), cy + int(7 * escala)), (cx + int(8 * escala), cy + int(12 * escala)), blue, -1)
        cv2.rectangle(
            img,
            (cx - int(5 * escala), cy + int(4 * escala)),
            (cx + int(5 * escala), cy + int(11 * escala)),
            suit_shadow,
            -1,
        )
        cv2.circle(img, (cx - int(2 * escala), cy + int(8 * escala)), max(1, int(2 * escala)), (0, 0, 255), -1, lineType=cv2.LINE_AA)
        cv2.circle(img, (cx + int(2 * escala), cy + int(8 * escala)), max(1, int(2 * escala)), (0, 200, 0), -1, lineType=cv2.LINE_AA)

        cv2.ellipse(
            img,
            (cx - int(16 * escala), cy + int(6 * escala)),
            (max(4, int(6 * escala)), max(7, int(9 * escala))),
            40,
            0,
            360,
            suit_white,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx + int(16 * escala), cy + int(10 * escala)),
            (max(4, int(6 * escala)), max(7, int(9 * escala))),
            -35,
            0,
            360,
            suit_white,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.circle(img, (cx - int(24 * escala), cy + int(9 * escala)), max(4, int(5 * escala)), gold, -1, lineType=cv2.LINE_AA)
        cv2.circle(img, (cx + int(23 * escala), cy + int(14 * escala)), max(4, int(5 * escala)), gold, -1, lineType=cv2.LINE_AA)

        cv2.ellipse(
            img,
            (cx - int(8 * escala), cy + int(26 * escala)),
            (max(5, int(7 * escala)), max(9, int(12 * escala))),
            25,
            0,
            360,
            suit_white,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx + int(8 * escala), cy + int(24 * escala)),
            (max(5, int(7 * escala)), max(9, int(12 * escala))),
            -30,
            0,
            360,
            suit_white,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx - int(10 * escala), cy + int(30 * escala)),
            (max(5, int(7 * escala)), max(3, int(5 * escala))),
            15,
            0,
            360,
            blue,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx + int(10 * escala), cy + int(28 * escala)),
            (max(5, int(7 * escala)), max(3, int(5 * escala))),
            -20,
            0,
            360,
            blue,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx - int(13 * escala), cy + int(38 * escala)),
            (max(5, int(7 * escala)), max(4, int(6 * escala))),
            20,
            0,
            360,
            gold,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx + int(13 * escala), cy + int(35 * escala)),
            (max(5, int(7 * escala)), max(4, int(6 * escala))),
            -20,
            0,
            360,
            gold,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx - int(12 * escala), cy + int(14 * escala)),
            (max(3, int(4 * escala)), max(3, int(5 * escala))),
            35,
            0,
            360,
            blue_dark,
            2,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            img,
            (cx + int(12 * escala), cy + int(18 * escala)),
            (max(3, int(4 * escala)), max(3, int(5 * escala))),
            -35,
            0,
            360,
            blue_dark,
            2,
            lineType=cv2.LINE_AA,
        )

    def _draw_explosion(self, entity, img, escala=1.0):
        cx, cy = int(entity.x), int(entity.y)

        if entity.frames_explosion_total <= 0:
            t = 0.0
        else:
            t = 1.0 - (entity.frames_explosion / float(entity.frames_explosion_total))
            t = max(0.0, min(1.0, t))

        max_radio = int(entity.size * 2.0 * escala)
        radio = max(4, int(max_radio * (0.4 + 0.6 * t)))

        if entity.tipo == "malo":
            ring_color = (0, 0, 255)
            inner_color = (0, 165, 255)

            ring_thickness = max(2, int(3 * (1.0 - t)))
            cv2.circle(img, (cx, cy), radio, ring_color, ring_thickness, lineType=cv2.LINE_AA)

            inner_radio = max(3, int(radio * 0.3))
            cv2.circle(img, (cx, cy), inner_radio, inner_color, -1, lineType=cv2.LINE_AA)

            for i in range(8):
                angle = (2 * math.pi / 8) * i + t * 3.0
                dist = radio * (0.6 + 0.4 * t)
                fx = int(cx + math.cos(angle) * dist)
                fy = int(cy + math.sin(angle) * dist)
                dx = int(math.cos(angle) * 6)
                dy = int(math.sin(angle) * 6)
                pts = np.array([[fx, fy], [fx - dy, fy + dx], [fx + dy, fy - dx]], dtype=np.int32)
                cv2.fillConvexPoly(img, pts, (200, 200, 255))
            return

        base_color = (255, 255, 255)
        inner_color = (255, 215, 0)

        halo = img.copy()
        cv2.circle(halo, (cx, cy), radio, base_color, -1, lineType=cv2.LINE_AA)
        alpha = 0.5 * (1.0 - t * 0.7)
        alpha = max(0.1, min(0.5, alpha))
        cv2.addWeighted(halo, alpha, img, 1.0 - alpha, 0, img)

        inner_radio = max(2, int(radio * 0.4))
        cv2.circle(img, (cx, cy), inner_radio, inner_color, -1, lineType=cv2.LINE_AA)

        for i in range(6):
            angle = (2 * math.pi / 6) * i + t * 4.0
            dist = radio * (0.6 + 0.5 * t)
            sx = int(cx + math.cos(angle) * dist)
            sy = int(cy + math.sin(angle) * dist)
            cv2.circle(img, (sx, sy), 2, inner_color, -1, lineType=cv2.LINE_AA)
