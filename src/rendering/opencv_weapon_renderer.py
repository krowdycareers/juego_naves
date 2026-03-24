"""Renderizado OpenCV para el arma del jugador."""

from __future__ import annotations

import math
import time
from pathlib import Path

import cv2
import numpy as np

from ..core import config


class OpenCVWeaponRenderer:
    """Dibuja el arma y sus efectos sobre frames OpenCV."""

    def __init__(self, sprite_dir=None):
        self.sprite_dir = Path(sprite_dir) if sprite_dir is not None else config.SPRITES_DIR
        self.weapon_frames = self._load_weapon_frames()

    def draw(self, weapon, img, x, y, size=1):
        """Dibuja el arma usando el estado actual del objeto Weapon."""
        if not self._draw_weapon_sprite(weapon, img, x, y, size):
            self._draw_fallback_weapon(weapon, img, x, y, size)

        return img

    def _load_weapon_frames(self):
        frames = []
        if not self.sprite_dir.exists():
            return frames

        for name in ("weapon_idle.png", "weapon_fire_1.png", "weapon_fire_2.png"):
            sprite = self._read_sprite(self.sprite_dir / name)
            if sprite is not None:
                frames.append(sprite)

        if not frames:
            sheet_path = self.sprite_dir / "weapon_sprite_sheet.png"
            if sheet_path.exists():
                sheet = self._read_sprite(sheet_path)
                if sheet is not None:
                    frame_count = 3
                    frame_w = sheet.shape[1] // frame_count
                    for index in range(frame_count):
                        frame = sheet[:, index * frame_w:(index + 1) * frame_w]
                        if frame.size > 0:
                            frames.append(frame)

        return frames

    def _read_sprite(self, path):
        if not Path(path).exists():
            return None

        sprite = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if sprite is None:
            return None

        if sprite.ndim == 2:
            sprite = cv2.cvtColor(sprite, cv2.COLOR_GRAY2BGRA)
        elif sprite.shape[2] == 3:
            alpha = np.full(sprite.shape[:2] + (1,), 255, dtype=np.uint8)
            sprite = np.concatenate([sprite, alpha], axis=2)

        return sprite

    def _draw_weapon_sprite(self, weapon, img, x, y, size):
        if not self.weapon_frames:
            return False

        frame = self._select_frame(weapon)
        if frame is None:
            return False

        sprite_scale = config.WEAPON_SPRITE_SCALE * size
        target_h = max(90, int(frame.shape[0] * sprite_scale))
        aspect = frame.shape[1] / max(1, frame.shape[0])
        target_w = max(56, int(target_h * aspect))
        sprite = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

        sight_x = int(target_w * config.WEAPON_SIGHT_ANCHOR_X)
        sight_y = max(2, int(target_h * config.WEAPON_SIGHT_ANCHOR_Y))
        x0 = int(x - sight_x)
        y0 = int(y - sight_y)

        self._blend_sprite(img, sprite, x0, y0)
        return True

    def _select_frame(self, weapon):
        if not self.weapon_frames:
            return None

        if not weapon.debe_mostrar_destello() or len(self.weapon_frames) == 1:
            return self.weapon_frames[0]

        fire_frames = self.weapon_frames[1:] if len(self.weapon_frames) > 1 else self.weapon_frames
        if not fire_frames:
            return self.weapon_frames[0]

        frame_index = int(time.time() * config.WEAPON_FIRE_ANIMATION_FPS) % len(fire_frames)
        return fire_frames[frame_index]

    def _blend_sprite(self, img, sprite, x, y):
        sprite_h, sprite_w = sprite.shape[:2]
        img_h, img_w = img.shape[:2]

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + sprite_w)
        y2 = min(img_h, y + sprite_h)

        if x1 >= x2 or y1 >= y2:
            return

        sx1 = x1 - x
        sy1 = y1 - y
        sx2 = sx1 + (x2 - x1)
        sy2 = sy1 + (y2 - y1)

        sprite_crop = sprite[sy1:sy2, sx1:sx2]
        rgb = sprite_crop[:, :, :3].astype(np.float32)
        alpha = sprite_crop[:, :, 3:4].astype(np.float32) / 255.0
        roi = img[y1:y2, x1:x2].astype(np.float32)
        img[y1:y2, x1:x2] = (rgb * alpha + roi * (1.0 - alpha)).astype(np.uint8)

    def _draw_fallback_weapon(self, weapon, img, x, y, size):
        """Mantiene el arma procedural si no existe el sprite real."""
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
        self._overlay_bgr(img, pistola, int(x - sight_x), int(y - sight_y))

    def _overlay_bgr(self, img, overlay, x, y):
        h, w = overlay.shape[:2]
        img_h, img_w = img.shape[:2]

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + w)
        y2 = min(img_h, y + h)
        if x1 >= x2 or y1 >= y2:
            return

        ox1 = x1 - x
        oy1 = y1 - y
        ox2 = ox1 + (x2 - x1)
        oy2 = oy1 + (y2 - y1)

        crop = overlay[oy1:oy2, ox1:ox2]
        roi = img[y1:y2, x1:x2]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        mask = gray > 5
        roi[mask] = crop[mask]
