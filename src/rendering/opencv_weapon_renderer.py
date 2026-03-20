"""Renderizado OpenCV para el arma del jugador."""

from __future__ import annotations

import math
import time

import cv2
import numpy as np


class OpenCVWeaponRenderer:
    """Dibuja el arma y sus efectos sobre frames OpenCV."""

    def draw(self, weapon, img, x, y, size=1):
        """Dibuja el arma usando el estado actual del objeto Weapon."""
        pistola = np.zeros((100, 85, 3), dtype=np.uint8)

        color_negro = (20, 20, 25)
        color_gris_oscuro = (45, 45, 50)
        color_gris_medio = (65, 65, 75)
        color_gris_claro = (100, 105, 115)

        cv2.circle(pistola, (42, 18), 14, color_negro, -1)
        cv2.circle(pistola, (42, 18), 12, color_gris_oscuro, -1)
        cv2.circle(pistola, (42, 18), 10, color_gris_medio, -1)

        energia_color_r = int(50 + 105 * weapon.energia_carga)
        energia_color_g = int(150 + 105 * weapon.energia_carga)
        energia_color_b = 220
        cv2.circle(pistola, (42, 18), 7, (energia_color_b, energia_color_g, energia_color_r), -1)
        cv2.circle(pistola, (42, 18), 4, (220, 220, 200), -1)

        for i in range(8):
            angle = (360 / 8) * i
            rad = math.radians(angle)
            x1 = int(42 + math.cos(rad) * 8)
            y1 = int(18 + math.sin(rad) * 8)
            x2 = int(42 + math.cos(rad) * 14)
            y2 = int(18 + math.sin(rad) * 14)
            cv2.line(pistola, (x1, y1), (x2, y2), (energia_color_b, energia_color_g, energia_color_r), 1)

        cv2.rectangle(pistola, (28, 8), (33, 38), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (51, 8), (56, 38), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (29, 10), (32, 36), color_gris_medio, -1)
        cv2.rectangle(pistola, (52, 10), (55, 36), color_gris_medio, -1)

        cv2.rectangle(pistola, (33, 6), (51, 12), color_gris_medio, -1)
        cv2.rectangle(pistola, (35, 7), (39, 11), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (41, 7), (44, 11), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (47, 7), (51, 11), color_gris_oscuro, -1)

        cv2.rectangle(pistola, (30, 38), (54, 50), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (32, 40), (52, 48), color_gris_medio, -1)
        for i in range(32, 52, 3):
            cv2.line(pistola, (i, 40), (i, 48), color_gris_oscuro, 1)

        cv2.rectangle(pistola, (34, 50), (50, 98), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (36, 52), (48, 96), color_gris_medio, -1)
        for i in range(52, 96, 2):
            cv2.line(pistola, (36, i), (48, i), color_negro, 1)

        cv2.ellipse(pistola, (42, 62), (11, 16), 0, 0, 180, color_gris_oscuro, -1)
        cv2.rectangle(pistola, (39, 55), (45, 70), color_gris_medio, -1)
        cv2.rectangle(pistola, (40, 57), (44, 68), color_gris_claro, -1)

        if weapon.armada:
            cv2.circle(pistola, (30, 42), 2, (0, 255, 0), -1)
        else:
            cv2.circle(pistola, (30, 42), 2, (0, 0, 255), -1)

        pistola = cv2.resize(
            pistola,
            (int(pistola.shape[1] * size), int(pistola.shape[0] * size)),
            interpolation=cv2.INTER_LINEAR,
        )

        sight_x = int(42 * size)
        sight_y = 0

        h, w = pistola.shape[:2]
        img_h, img_w = img.shape[:2]

        x0 = int(x - sight_x)
        y0 = int(y - sight_y)

        if x0 >= img_w or y0 >= img_h or x0 + w <= 0 or y0 + h <= 0:
            return img

        pistola_crop = pistola.copy()
        if x0 + w > img_w:
            pistola_crop = pistola_crop[:, :img_w - x0]
            w = pistola_crop.shape[1]
        if y0 + h > img_h:
            pistola_crop = pistola_crop[:img_h - y0, :]
            h = pistola_crop.shape[0]

        if x0 < 0:
            pistola_crop = pistola_crop[:, -x0:]
            w = pistola_crop.shape[1]
            x0 = 0
        if y0 < 0:
            pistola_crop = pistola_crop[-y0:, :]
            h = pistola_crop.shape[0]
            y0 = 0

        if h > 0 and w > 0:
            roi = img[y0:y0+h, x0:x0+w]
            gray = cv2.cvtColor(pistola_crop, cv2.COLOR_BGR2GRAY)
            mask = gray > 5
            roi[mask] = pistola_crop[mask]

        if weapon.debe_mostrar_destello():
            cv2.circle(img, (x, y), 3, (0, 255, 255), -1)
            cv2.circle(img, (x, y), 2, (255, 255, 100), -1)
            cv2.line(img, (x - 8, y), (x + 8, y), (0, 255, 255), 1)
            cv2.line(img, (x, y - 8), (x, y + 8), (0, 255, 255), 1)

            flash_intensity = (math.sin(time.time() * 30) + 1) / 2
            flash_intensity = max(0.5, flash_intensity)

            flash_r1 = max(12, int(16 * size * flash_intensity))
            color1 = (
                int(0 * flash_intensity),
                int(165 * flash_intensity),
                int(255 * flash_intensity),
            )
            cv2.circle(img, (x, y), flash_r1, color1, -1)

            flash_r2 = max(6, int(8 * size * flash_intensity))
            cv2.circle(img, (x, y), flash_r2, (255, 255, 255), -1)

            for i in range(8):
                ang = (360 / 8) * i + (time.time() * 60 % 360)
                rad = math.radians(ang)
                flash_length = max(15, int(22 * size))
                x2 = int(x + math.cos(rad) * flash_length)
                y2 = int(y + math.sin(rad) * flash_length)

                ray_color = (
                    int(0 * flash_intensity),
                    int(200 * flash_intensity),
                    int(255 * flash_intensity),
                )
                cv2.line(img, (x, y), (x2, y2), ray_color, max(1, int(2 * size)))

            flash_r3 = max(20, int(28 * size * flash_intensity))
            ring_color = (0, int(100 * flash_intensity), int(200 * flash_intensity))
            cv2.circle(img, (x, y), flash_r3, ring_color, max(1, int(2 * size)))

        return img
