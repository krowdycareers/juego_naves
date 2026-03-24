"""Renderizado OpenCV para entidades del juego."""

from __future__ import annotations

import math
import time
from pathlib import Path

import cv2
import numpy as np

from ..core import config


class OpenCVEntityRenderer:
    """Dibuja entidades del juego sobre frames de OpenCV."""

    def __init__(self, sprite_dir=None):
        self.sprite_dir = Path(sprite_dir) if sprite_dir is not None else config.SPRITES_DIR
        self.ship_sprites = {
            "bueno": self._load_ship_sprite_set("player_ship"),
            "malo": self._load_ship_sprite_set("enemy_ship"),
        }

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
        elif self._draw_ship_sprite(entity, img, escala):
            return
        elif entity.tipo == "malo":
            self._draw_enemy_ship(entity, img, escala)
        else:
            self._draw_friendly_ship(entity, img, escala)

    def _load_ship_sprite_set(self, base_name):
        sprite_set = {}
        if not self.sprite_dir.exists():
            return sprite_set

        sheet_path = self.sprite_dir / f"{base_name}_sheet.png"
        if sheet_path.exists():
            sprite_set.update(self._split_sprite_sheet(sheet_path))

        for pose in ("center", "left", "right", "rear_left", "rear_center", "rear_right"):
            sprite_path = self.sprite_dir / f"{base_name}_{pose}.png"
            sprite = self._read_sprite(sprite_path)
            if sprite is not None:
                sprite_set[pose] = sprite

        single_path = self.sprite_dir / f"{base_name}.png"
        single_sprite = self._read_sprite(single_path)
        if single_sprite is not None:
            sprite_set.setdefault("center", single_sprite)

        return sprite_set

    def _split_sprite_sheet(self, sheet_path):
        sprite_sheet = self._read_sprite(sheet_path)
        if sprite_sheet is None:
            return {}

        height, width = sprite_sheet.shape[:2]
        if width < 3 or height < 2:
            return {"center": sprite_sheet}

        cell_w = width // 3
        cell_h = height // 2
        poses = {
            "left": sprite_sheet[0:cell_h, 0:cell_w],
            "center": sprite_sheet[0:cell_h, cell_w:cell_w * 2],
            "right": sprite_sheet[0:cell_h, cell_w * 2:cell_w * 3],
            "rear_left": sprite_sheet[cell_h:cell_h * 2, 0:cell_w],
            "rear_center": sprite_sheet[cell_h:cell_h * 2, cell_w:cell_w * 2],
            "rear_right": sprite_sheet[cell_h:cell_h * 2, cell_w * 2:cell_w * 3],
        }

        return {
            key: value
            for key, value in poses.items()
            if value.size > 0
        }

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

    def _draw_ship_sprite(self, entity, img, escala):
        sprite_set = self.ship_sprites.get(entity.tipo) or {}
        if not sprite_set:
            return False

        pose = self._select_sprite_pose(entity, sprite_set)
        sprite = sprite_set.get(pose)
        if sprite is None:
            sprite = sprite_set.get("center")
        if sprite is None:
            return False

        sprite_scale = config.PLAYER_SPRITE_SCALE if entity.tipo == "bueno" else config.ENEMY_SPRITE_SCALE
        target_h = max(18, int(sprite.shape[0] * escala * sprite_scale))
        aspect_ratio = sprite.shape[1] / max(1, sprite.shape[0])
        target_w = max(28, int(target_h * aspect_ratio))
        resized = cv2.resize(sprite, (target_w, target_h), interpolation=cv2.INTER_AREA)

        motion = self._motion_state(entity, escala, phase_speed=7.2 if entity.tipo == "bueno" else 6.6)
        cx, cy = motion["center"]
        top_left_x = int(cx - target_w / 2)
        top_left_y = int(cy - target_h / 2)

        self._draw_shadow(
            img,
            (cx, cy + int(target_h * 0.34)),
            (target_w * 0.28, target_h * 0.10),
            alpha=0.18,
        )
        self._blend_sprite(img, resized, top_left_x, top_left_y)
        self._draw_sprite_engine_trail(entity, img, resized, top_left_x, top_left_y, motion["trail_dir"])
        return True

    def _select_sprite_pose(self, entity, sprite_set):
        vx = float(getattr(entity, "vx", 0.0))
        vy = float(getattr(entity, "vy", 0.0))
        abs_vx = abs(vx)
        abs_vy = abs(vy)

        if abs_vy > abs_vx * 1.15:
            if vy > 0:
                if vx < -0.8 and "rear_left" in sprite_set:
                    return "rear_left"
                if vx > 0.8 and "rear_right" in sprite_set:
                    return "rear_right"
                if "rear_center" in sprite_set:
                    return "rear_center"
            if "center" in sprite_set:
                return "center"

        if vx < -0.8 and "left" in sprite_set:
            return "left"
        if vx > 0.8 and "right" in sprite_set:
            return "right"
        return "center"

    def _blend_sprite(self, img, sprite, x, y):
        sprite_h, sprite_w = sprite.shape[:2]
        img_h, img_w = img.shape[:2]

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + sprite_w)
        y2 = min(img_h, y + sprite_h)

        if x1 >= x2 or y1 >= y2:
            return

        sprite_x1 = x1 - x
        sprite_y1 = y1 - y
        sprite_x2 = sprite_x1 + (x2 - x1)
        sprite_y2 = sprite_y1 + (y2 - y1)

        sprite_crop = sprite[sprite_y1:sprite_y2, sprite_x1:sprite_x2]
        rgb = sprite_crop[:, :, :3].astype(np.float32)
        alpha = (sprite_crop[:, :, 3:4].astype(np.float32) / 255.0)
        roi = img[y1:y2, x1:x2].astype(np.float32)
        blended = rgb * alpha + roi * (1.0 - alpha)
        img[y1:y2, x1:x2] = blended.astype(np.uint8)

    def _draw_sprite_engine_trail(self, entity, img, sprite, x, y, direction):
        h, w = sprite.shape[:2]
        color = (70, 185, 255) if entity.tipo == "bueno" else (80, 210, 150)
        alpha = 0.15 if entity.tipo == "bueno" else 0.18

        start_points = [
            (x + int(w * 0.28), y + int(h * 0.82)),
            (x + int(w * 0.72), y + int(h * 0.82)),
        ]
        for start in start_points:
            self._draw_thruster_trail(
                img,
                start,
                direction,
                length=max(12, int(h * 0.35)),
                color=color,
                alpha=alpha,
                width=max(3, int(w * 0.06)),
            )

    def _draw_enemy_ship(self, entity, img, escala=1.0):
        motion = self._motion_state(entity, escala, phase_speed=6.8)
        cx, cy = motion["center"]
        drift = motion["drift"]
        trail_dir = motion["trail_dir"]
        body_w = max(54, int(74 * escala))
        body_h = max(30, int(42 * escala))
        core_r = max(13, int(18 * escala))
        blink_phase = time.time() * 7.5

        self._draw_thruster_trail(
            img,
            (cx, cy + int(body_h * 0.30)),
            trail_dir,
            length=max(16, int(24 * escala)),
            color=(80, 210, 150),
            alpha=0.18,
            width=max(5, int(8 * escala)),
        )
        self._draw_shadow(img, (cx, cy + int(body_h * 0.55)), (body_w * 0.42, body_h * 0.18), alpha=0.24)
        self._draw_vertical_glow(
            img,
            (cx, cy + int(body_h * 0.18)),
            radius=max(24, int(30 * escala)),
            color=(60, 220, 140),
            alpha=0.14,
        )

        body = np.array(
            [
                [cx - int(body_w * 0.34), cy - int(body_h * 0.10) + int(drift * 0.2)],
                [cx - int(body_w * 0.20), cy - int(body_h * 0.36) - int(drift * 0.4)],
                [cx + int(body_w * 0.20), cy - int(body_h * 0.36) + int(drift * 0.4)],
                [cx + int(body_w * 0.34), cy - int(body_h * 0.10) - int(drift * 0.2)],
                [cx + int(body_w * 0.22), cy + int(body_h * 0.18)],
                [cx - int(body_w * 0.22), cy + int(body_h * 0.18)],
            ],
            dtype=np.int32,
        )
        self._fill_poly_with_outline(img, body, fill=(62, 70, 86), outline=(18, 24, 34), thickness=max(2, int(2 * escala)))

        core_center = (cx, cy - int(body_h * 0.03))
        cv2.circle(img, core_center, core_r, (94, 106, 126), -1, cv2.LINE_AA)
        cv2.circle(img, core_center, max(5, int(core_r * 0.55)), (24, 32, 42), -1, cv2.LINE_AA)
        cv2.circle(img, core_center, max(3, int(core_r * 0.28)), (182, 255, 225), -1, cv2.LINE_AA)
        cv2.circle(img, core_center, core_r, (18, 24, 34), max(1, int(2 * escala)), cv2.LINE_AA)

        for side in (-1, 1):
            joint = (cx + int(side * body_w * 0.24), cy + int(body_h * 0.01))
            claw_root = (cx + int(side * body_w * 0.42), cy + int(body_h * 0.12))
            claw_tip = (cx + int(side * body_w * 0.31), cy + int(body_h * 0.43) + int(drift * side * 0.3))
            blade = np.array(
                [
                    [joint[0], joint[1]],
                    [claw_root[0], claw_root[1] - int(body_h * 0.06)],
                    [claw_tip[0], claw_tip[1]],
                    [claw_root[0] - int(side * body_w * 0.05), claw_root[1] + int(body_h * 0.06)],
                ],
                dtype=np.int32,
            )
            cv2.line(img, joint, claw_root, (50, 57, 70), max(3, int(5 * escala)), cv2.LINE_AA)
            cv2.circle(img, joint, max(4, int(5 * escala)), (95, 104, 118), -1, cv2.LINE_AA)
            self._fill_poly_with_outline(img, blade, fill=(90, 188, 56), outline=(35, 55, 28), thickness=max(2, int(2 * escala)))

        cannon = np.array(
            [
                [cx - int(body_w * 0.18), cy - int(body_h * 0.30)],
                [cx - int(body_w * 0.52), cy - int(body_h * 0.30)],
                [cx - int(body_w * 0.58), cy - int(body_h * 0.18)],
                [cx - int(body_w * 0.18), cy - int(body_h * 0.14)],
            ],
            dtype=np.int32,
        )
        self._fill_poly_with_outline(img, cannon, fill=(104, 168, 44), outline=(34, 52, 26), thickness=max(2, int(2 * escala)))
        cv2.rectangle(
            img,
            (cx - int(body_w * 0.06), cy - int(body_h * 0.25)),
            (cx + int(body_w * 0.06), cy - int(body_h * 0.18)),
            (30, 92, 148),
            -1,
        )

        for index, offset in enumerate((-0.12, 0.0, 0.12)):
            thruster = (cx + int(offset * body_w), cy + int(body_h * 0.36))
            cv2.circle(img, thruster, max(4, int(5 * escala)), (28, 34, 44), -1, cv2.LINE_AA)
            flame = img.copy()
            pulse = 0.65 + 0.35 * max(0.0, math.sin(blink_phase + offset * 8.0))
            cv2.ellipse(
                flame,
                (thruster[0], thruster[1] + max(6, int(7 * escala))),
                (max(3, int(4 * escala)), max(6, int(8 * escala))),
                0,
                0,
                360,
                (80, int(170 + 50 * pulse), 255),
                -1,
                cv2.LINE_AA,
            )
            cv2.addWeighted(flame, 0.22, img, 0.78, 0, img)
            if index != 1:
                self._draw_thruster_trail(
                    img,
                    (thruster[0], thruster[1] + max(4, int(4 * escala))),
                    trail_dir,
                    length=max(10, int(14 * escala)),
                    color=(130, 255, 190),
                    alpha=0.12,
                    width=max(3, int(4 * escala)),
                )

    def _draw_friendly_ship(self, entity, img, escala=1.0):
        motion = self._motion_state(entity, escala, phase_speed=7.6)
        cx, cy = motion["center"]
        drift = motion["drift"]
        trail_dir = motion["trail_dir"]
        pose = self._ship_pose(entity)
        body_w = max(52, int(70 * escala))
        body_h = max(34, int(48 * escala))
        engine_phase = time.time() * 8.2
        bank = pose["bank"]
        pitch = pose["pitch"]
        wing_push = pose["wing_push"]
        rear_lift = pose["rear_lift"]
        nose_shift = pose["nose_shift"]

        self._draw_thruster_trail(
            img,
            (cx, cy + int(body_h * 0.32)),
            trail_dir,
            length=max(18, int(24 * escala)),
            color=(70, 185, 255),
            alpha=0.16,
            width=max(5, int(8 * escala)),
        )
        self._draw_shadow(img, (cx, cy + int(body_h * 0.58)), (body_w * 0.34, body_h * 0.16), alpha=0.22)
        self._draw_vertical_glow(
            img,
            (cx, cy + int(body_h * 0.16)),
            radius=max(22, int(26 * escala)),
            color=(255, 190, 70),
            alpha=0.10,
        )

        left_wing = np.array(
            [
                [cx - int(body_w * 0.18), cy + int(body_h * 0.04) + int(drift * 0.25) + int(bank * 0.2)],
                [cx - int(body_w * (0.48 + wing_push * 0.04)), cy + int(body_h * 0.18) + int(rear_lift * 0.3)],
                [cx - int(body_w * 0.30), cy - int(body_h * (0.24 + pitch * 0.05)) - int(drift * 0.35)],
                [cx - int(body_w * 0.08), cy - int(body_h * 0.12) - int(bank * 0.15)],
            ],
            dtype=np.int32,
        )
        right_wing = np.array(
            [
                [cx + int(body_w * 0.18), cy + int(body_h * 0.04) - int(drift * 0.25) - int(bank * 0.2)],
                [cx + int(body_w * (0.48 - wing_push * 0.04)), cy + int(body_h * 0.18) - int(rear_lift * 0.3)],
                [cx + int(body_w * 0.30), cy - int(body_h * (0.24 - pitch * 0.05)) + int(drift * 0.35)],
                [cx + int(body_w * 0.08), cy - int(body_h * 0.12) + int(bank * 0.15)],
            ],
            dtype=np.int32,
        )
        fuselage = np.array(
            [
                [cx + int(nose_shift * 0.45), cy - int(body_h * (0.44 + pitch * 0.08))],
                [cx + int(body_w * (0.12 - bank * 0.001)), cy - int(body_h * 0.06)],
                [cx + int(body_w * 0.10), cy + int(body_h * (0.30 - rear_lift * 0.04))],
                [cx, cy + int(body_h * (0.44 - rear_lift * 0.05))],
                [cx - int(body_w * 0.10), cy + int(body_h * (0.30 + rear_lift * 0.04))],
                [cx - int(body_w * (0.12 + bank * 0.001)), cy - int(body_h * 0.06)],
            ],
            dtype=np.int32,
        )

        self._fill_poly_with_outline(img, left_wing, fill=(224, 138, 42), outline=(120, 68, 18), thickness=max(2, int(2 * escala)))
        self._fill_poly_with_outline(img, right_wing, fill=(224, 138, 42), outline=(120, 68, 18), thickness=max(2, int(2 * escala)))
        self._fill_poly_with_outline(img, fuselage, fill=(228, 238, 246), outline=(120, 132, 150), thickness=max(2, int(2 * escala)))

        cockpit = np.array(
            [
                [cx + int(nose_shift * 0.25), cy - int(body_h * (0.28 + pitch * 0.04))],
                [cx + int(body_w * 0.08) - int(bank * 0.12), cy - int(body_h * 0.02)],
                [cx, cy + int(body_h * 0.14)],
                [cx - int(body_w * 0.08) - int(bank * 0.12), cy - int(body_h * 0.02)],
            ],
            dtype=np.int32,
        )
        self._fill_poly_with_outline(img, cockpit, fill=(255, 214, 90), outline=(188, 128, 25), thickness=max(1, int(2 * escala)))
        cv2.line(
            img,
            (cx, cy - int(body_h * 0.20)),
            (cx, cy + int(body_h * 0.10)),
            (255, 247, 180),
            max(1, int(2 * escala)),
            cv2.LINE_AA,
        )

        nose_glow = img.copy()
        cv2.circle(
            nose_glow,
            (cx + int(nose_shift * 0.45), cy - int(body_h * (0.44 + pitch * 0.08))),
            max(4, int(5 * escala)),
            (255, 245, 180),
            -1,
            cv2.LINE_AA,
        )
        cv2.addWeighted(nose_glow, 0.18, img, 0.82, 0, img)

        for side in (-1, 1):
            engine = (
                cx + int(side * body_w * (0.14 + wing_push * 0.01)),
                cy + int(body_h * (0.28 - rear_lift * 0.03)) + int(bank * side * 0.18),
            )
            cv2.circle(img, engine, max(4, int(5 * escala)), (92, 104, 126), -1, cv2.LINE_AA)
            flame = img.copy()
            pulse = 0.55 + 0.45 * max(0.0, math.sin(engine_phase + side))
            cv2.ellipse(
                flame,
                (engine[0], engine[1] + max(7, int(8 * escala))),
                (max(4, int(5 * escala)), max(8, int(11 * escala))),
                0,
                0,
                360,
                (int(40 + 90 * pulse), int(160 + 70 * pulse), 255),
                -1,
                cv2.LINE_AA,
            )
            cv2.addWeighted(flame, 0.22, img, 0.78, 0, img)
            self._draw_thruster_trail(
                img,
                (engine[0], engine[1] + max(3, int(4 * escala))),
                trail_dir,
                length=max(10, int(16 * escala)),
                color=(160, 225, 255),
                alpha=0.12,
                width=max(3, int(5 * escala)),
            )

        stripe = np.array(
            [
                [cx - int(body_w * 0.06), cy - int(body_h * 0.02)],
                [cx + int(body_w * 0.06), cy - int(body_h * 0.02)],
                [cx + int(body_w * 0.12), cy + int(body_h * 0.18)],
                [cx - int(body_w * 0.12), cy + int(body_h * 0.18)],
            ],
            dtype=np.int32,
        )
        cv2.fillConvexPoly(img, stripe, (60, 160, 255), lineType=cv2.LINE_AA)

    def _draw_shadow(self, img, center, axes, alpha=0.2):
        shadow = img.copy()
        cv2.ellipse(
            shadow,
            center,
            (max(4, int(axes[0])), max(2, int(axes[1]))),
            0,
            0,
            360,
            (20, 20, 30),
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.addWeighted(shadow, alpha, img, 1.0 - alpha, 0, img)

    def _draw_vertical_glow(self, img, center, radius, color, alpha=0.12):
        glow = img.copy()
        cv2.circle(glow, center, max(6, int(radius)), color, -1, cv2.LINE_AA)
        cv2.addWeighted(glow, alpha, img, 1.0 - alpha, 0, img)

    def _motion_state(self, entity, escala, phase_speed):
        phase = time.time() * phase_speed + (entity.x * 0.013) + (entity.y * 0.009)
        bob_x = math.sin(phase) * max(1.0, 1.6 * escala)
        bob_y = math.cos(phase * 1.15) * max(1.0, 1.8 * escala)
        vx = float(getattr(entity, "vx", 0.0))
        vy = float(getattr(entity, "vy", 0.0))
        speed = math.hypot(vx, vy)

        if speed > 0.01:
            trail_dir = (-vx / speed, -vy / speed)
        else:
            trail_dir = (0.0, 1.0)

        drift = math.sin(phase * 1.3) * min(6.0, speed * 0.18 + 2.0)
        return {
            "center": (int(entity.x + bob_x), int(entity.y + bob_y)),
            "trail_dir": trail_dir,
            "drift": drift,
        }

    def _ship_pose(self, entity):
        vx = float(getattr(entity, "vx", 0.0))
        vy = float(getattr(entity, "vy", 0.0))
        bank = max(-1.0, min(1.0, vx / 10.0))
        pitch = max(-1.0, min(1.0, -vy / 10.0))
        return {
            "bank": bank * 10.0,
            "pitch": pitch,
            "wing_push": abs(bank),
            "rear_lift": pitch,
            "nose_shift": bank * 10.0,
        }

    def _draw_thruster_trail(self, img, start, direction, length, color, alpha=0.14, width=6):
        dx, dy = direction
        if abs(dx) < 1e-4 and abs(dy) < 1e-4:
            dx, dy = 0.0, 1.0

        trail = img.copy()
        end = (int(start[0] + dx * length), int(start[1] + dy * length))
        cv2.line(trail, start, end, color, max(1, width), cv2.LINE_AA)
        cv2.circle(trail, end, max(2, width // 2), color, -1, cv2.LINE_AA)
        cv2.addWeighted(trail, alpha, img, 1.0 - alpha, 0, img)

        smoke = img.copy()
        for step in range(1, 4):
            t = step / 3.0
            px = int(start[0] + dx * length * t)
            py = int(start[1] + dy * length * t)
            radius = max(2, int(width * (0.35 + t * 0.35)))
            tone = int(90 + 40 * t)
            cv2.circle(smoke, (px, py), radius, (tone, tone, tone), -1, cv2.LINE_AA)
        cv2.addWeighted(smoke, alpha * 0.45, img, 1.0 - alpha * 0.45, 0, img)

    def _fill_poly_with_outline(self, img, pts, fill, outline, thickness=2):
        cv2.fillConvexPoly(img, pts, fill, lineType=cv2.LINE_AA)
        cv2.polylines(img, [pts], isClosed=True, color=outline, thickness=thickness, lineType=cv2.LINE_AA)

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
