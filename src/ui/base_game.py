"""Lógica compartida del ciclo principal del juego para la app basada en pygame."""

from __future__ import annotations

import cv2
import mediapipe as mp
import numpy as np
import time

from ..core import config
from ..core.camera_manager import CameraManager
from ..game.game_engine import GameEngine
from ..rendering import OpenCVEntityRenderer, OpenCVWeaponRenderer


class BaseGameApp:
    """Base de la aplicación de juego con captura/procesamiento desacoplados de la ventana."""

    def __init__(self, camera_index=None, background_path=None, weapon=None):
        self.camera_manager = CameraManager(
            mode=config.CAMERA_MODE,
            cam_index=camera_index,
            screen_index=config.SCREEN_INDEX,
            max_cam_search=config.CAMERA_MAX_SEARCH,
            fullscreen=config.FULLSCREEN,
        )

        self.width = self.camera_manager.width
        self.height = self.camera_manager.height
        self.background = self._load_background(background_path)
        self.parallax_layers = self._build_background_layers(self.background)
        self._background_time = time.time()

        mp_hands = mp.solutions.hands
        print("[DEBUG] Inicializando MediaPipe...")
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        print("[DEBUG] MediaPipe inicializado")

        print("[DEBUG] Inicializando GameEngine...")
        self.engine = GameEngine(self.width, self.height, weapon=weapon)
        print("[DEBUG] GameEngine inicializado")
        self.engine.weapon.iniciar_ambiente()
        self.entity_renderer = OpenCVEntityRenderer()
        self.weapon_renderer = OpenCVWeaponRenderer()

        self.show_background = True
        self.show_hand_points = False
        self.last_frame_time = time.time()
        self.pistola_x = 0
        self.pistola_y = 0
        self.show_pistola = False
        self.display_score = float(self.engine.get_score())
        self.last_score_value = self.engine.get_score()
        self.score_pulse_until = 0.0
        self.score_flash_color = (255, 255, 255)
        self.hit_feedbacks = []
        print("[DEBUG] BaseGameApp inicializado completamente")

    def _load_background(self, bg_path=None):
        """Carga la imagen de fondo por defecto o una personalizada."""
        if bg_path:
            bg = cv2.imread(bg_path)
            if bg is not None:
                result = self._prepare_background(bg)
                print(f"[DEBUG] Fondo cargado desde: {bg_path}, shape={result.shape}")
                return result

        for fallback_path in config.FALLBACK_BACKGROUND_PATHS:
            bg = cv2.imread(str(fallback_path))
            if bg is not None:
                result = self._prepare_background(bg)
                print(f"[DEBUG] Fondo cargado desde fallback: {fallback_path}, shape={result.shape}")
                return result

        print("[DEBUG] No se encontró imagen de fondo, usando fondo negro")
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def _prepare_background(self, bg):
        """Recorta y ajusta el color del fondo para que funcione mejor como escena espacial."""
        cropped = self._crop_background(bg)
        resized = cv2.resize(cropped, (self.width, self.height), interpolation=cv2.INTER_AREA)
        return self._grade_background(resized)

    def _crop_background(self, bg):
        """Recorta la zona inferior menos útil para privilegiar cielo y profundidad."""
        img_h = bg.shape[0]
        top = int(img_h * float(config.BACKGROUND_CROP_TOP))
        bottom = int(img_h * (1.0 - float(config.BACKGROUND_CROP_BOTTOM)))
        bottom = max(top + 1, min(img_h, bottom))
        return bg[top:bottom, :]

    def _grade_background(self, bg):
        """Aplica un tratamiento frío y sutil para acercar el fondo a una estética sci-fi."""
        if not config.BACKGROUND_COLOR_GRADE_ENABLED:
            return bg

        graded = bg.astype(np.float32)
        graded = (graded - 127.5) * float(config.BACKGROUND_CONTRAST) + 127.5
        graded *= float(config.BACKGROUND_BRIGHTNESS)
        graded[:, :, 0] *= float(config.BACKGROUND_BLUE_GAIN)
        graded[:, :, 1] *= float(config.BACKGROUND_GREEN_GAIN)
        graded[:, :, 2] *= float(config.BACKGROUND_RED_GAIN)
        graded = np.clip(graded, 0, 255)

        haze_alpha = float(config.BACKGROUND_HAZE_ALPHA)
        if haze_alpha > 0.0:
            haze = np.zeros_like(graded)
            gradient = np.linspace(0.0, 1.0, self.height, dtype=np.float32)[:, None]
            haze[:, :, 0] = 36 + gradient * 18
            haze[:, :, 1] = 18 + gradient * 12
            haze[:, :, 2] = 10 + gradient * 8
            graded = cv2.addWeighted(graded, 1.0, haze, haze_alpha, 0.0)

        vignette_x = np.linspace(-1.0, 1.0, self.width, dtype=np.float32)
        vignette_y = np.linspace(-1.0, 1.0, self.height, dtype=np.float32)
        grid_x, grid_y = np.meshgrid(vignette_x, vignette_y)
        vignette = 1.0 - 0.18 * np.clip(np.sqrt(grid_x * grid_x + grid_y * grid_y), 0.0, 1.0)
        graded *= vignette[:, :, None]

        return np.clip(graded, 0, 255).astype(np.uint8)

    def _build_background_layers(self, base_background):
        """Prepara capas parallax como campos de estrellas sobre el fondo base."""
        if not config.BACKGROUND_PARALLAX_ENABLED:
            return []

        rng = np.random.default_rng(7)
        layers = []
        for layer_cfg in config.BACKGROUND_PARALLAX_LAYERS:
            layers.append(
                {
                    "name": layer_cfg["name"],
                    "alpha": float(layer_cfg["alpha"]),
                    "trail": float(layer_cfg.get("trail", 0.0)),
                    "color": tuple(int(v) for v in layer_cfg.get("color", (255, 255, 255))),
                    "speed_x": config.BACKGROUND_PARALLAX_BASE_SPEED_X * float(layer_cfg["speed_x"]),
                    "speed_y": config.BACKGROUND_PARALLAX_BASE_SPEED_Y * float(layer_cfg["speed_y"]),
                    "stars": self._generate_star_positions(rng, layer_cfg),
                }
            )

        if layers:
            print(f"[DEBUG] Fondo parallax inicializado con {len(layers)} capas")
        return layers

    def _generate_star_positions(self, rng, layer_cfg):
        """Genera estrellas iniciales para una capa parallax."""
        count = max(0, int(layer_cfg.get("count", 0)))
        radius_min = max(1, int(layer_cfg.get("radius_min", 1)))
        radius_max = max(radius_min, int(layer_cfg.get("radius_max", radius_min)))
        stars = []
        for _ in range(count):
            stars.append(
                {
                    "x": float(rng.uniform(0, self.width)),
                    "y": float(rng.uniform(0, self.height)),
                    "radius": int(rng.integers(radius_min, radius_max + 1)),
                }
            )
        return stars

    def _update_parallax_layer(self, layer, delta):
        """Actualiza posiciones de las estrellas y las hace reaparecer por wrapping."""
        for star in layer["stars"]:
            star["x"] += layer["speed_x"] * delta
            star["y"] += layer["speed_y"] * delta

            if star["x"] < -star["radius"]:
                star["x"] = self.width + star["radius"]
            elif star["x"] > self.width + star["radius"]:
                star["x"] = -star["radius"]

            if star["y"] < -star["radius"]:
                star["y"] = self.height + star["radius"]
            elif star["y"] > self.height + star["radius"]:
                star["y"] = -star["radius"]

    def _draw_parallax_layer(self, base_img, layer):
        """Dibuja una capa de estrellas con trazo opcional."""
        overlay = np.zeros_like(base_img)
        for star in layer["stars"]:
            center = (int(round(star["x"])), int(round(star["y"])))
            radius = int(star["radius"])

            trail = float(layer["trail"])
            if trail > 0.0:
                trail_end = (
                    int(round(star["x"] - layer["speed_x"] * trail)),
                    int(round(star["y"] - layer["speed_y"] * trail)),
                )
                cv2.line(overlay, trail_end, center, layer["color"], max(1, radius), cv2.LINE_AA)

            cv2.circle(overlay, center, radius, layer["color"], -1, cv2.LINE_AA)

        return cv2.addWeighted(base_img, 1.0, overlay, layer["alpha"], 0.0)

    def _compose_parallax_background(self):
        """Compone el fondo base con capas de estrellas en movimiento."""
        if not self.parallax_layers:
            return self.background.copy()

        current_time = time.time()
        delta = max(0.0, min(0.05, current_time - self._background_time))
        self._background_time = current_time

        composed = self.background.copy()
        for layer in self.parallax_layers:
            self._update_parallax_layer(layer, delta)
            composed = self._draw_parallax_layer(composed, layer)

        return composed

    def _process_hand_landmarks(self, results, cam_img):
        """Procesa los landmarks de la mano y actualiza el arma."""
        firing = False
        pointer_x = self.pistola_x
        pointer_y = self.pistola_y

        if not results.multi_hand_landmarks:
            return firing, pointer_x, pointer_y

        cam_h, cam_w = cam_img.shape[:2]

        for hand_lms in results.multi_hand_landmarks:
            landmarks = {}
            for idx, lm in enumerate(hand_lms.landmark):
                cx = int((lm.x * cam_w / self.width) * self.width)
                cy = int((lm.y * cam_h / self.height) * self.height)
                landmarks[idx] = (cx, cy)

            if all(key in landmarks for key in [2, 3, 4, 8]):
                firing = self.engine.weapon.actualizar_estado(landmarks)
                pointer_x, pointer_y = landmarks[8]

                if firing:
                    target = self._find_entity_under_pointer(pointer_x, pointer_y)
                    self.engine.weapon.reproducir_sonido()
                    hit = self.engine.process_shot(pointer_x, pointer_y)
                    if hit and target is not None:
                        self._register_hit_feedback(target, pointer_x, pointer_y)

                self.show_pistola = True
                self.pistola_x = pointer_x
                self.pistola_y = pointer_y

        return firing, pointer_x, pointer_y

    def _find_entity_under_pointer(self, pointer_x, pointer_y):
        """Retorna la primera entidad impactable bajo la mira."""
        for entity in self.engine.entities:
            if not entity.activo or entity.en_explosion:
                continue
            if entity.contiene_punto_disparo(
                pointer_x,
                pointer_y,
                alto_total=self.height,
                padding=config.HITBOX_PADDING + config.WEAPON_RETICLE_HIT_PADDING,
            ):
                return entity
        return None

    def _register_hit_feedback(self, entity, pointer_x, pointer_y):
        """Guarda un feedback visual temporal para impactos y score."""
        now = time.time()
        if entity.tipo == "malo":
            label = f"+{config.SHOT_SCORE_ENEMY}"
            color = (90, 255, 140)
        else:
            label = f"-{config.SHOT_SCORE_PENALTY_FRIENDLY}"
            color = (90, 120, 255)

        self.hit_feedbacks.append(
            {
                "label": label,
                "color": color,
                "x": int(pointer_x),
                "y": int(pointer_y),
                "created_at": now,
                "duration": 0.7,
            }
        )
        self.score_pulse_until = now + 0.35
        self.score_flash_color = color

    def _draw_rounded_panel(self, img, top_left, bottom_right, fill_color, border_color, alpha=0.8, radius=18):
        """Dibuja un panel translúcido con borde redondeado."""
        overlay = img.copy()
        cv2.rectangle(overlay, top_left, bottom_right, fill_color, -1)
        cv2.rectangle(overlay, top_left, bottom_right, border_color, 2)
        x1, y1 = top_left
        x2, y2 = bottom_right
        for corner in (
            (x1 + radius, y1 + radius),
            (x2 - radius, y1 + radius),
            (x1 + radius, y2 - radius),
            (x2 - radius, y2 - radius),
        ):
            cv2.circle(overlay, corner, radius, fill_color, -1, cv2.LINE_AA)
            cv2.circle(overlay, corner, radius, border_color, 2, cv2.LINE_AA)
        cv2.addWeighted(overlay, alpha, img, 1.0 - alpha, 0.0, img)

    def _draw_bar(self, img, x, y, width, height, progress, fill_color, background_color, border_color):
        """Dibuja una barra horizontal simple."""
        progress = max(0.0, min(1.0, float(progress)))
        cv2.rectangle(img, (x, y), (x + width, y + height), background_color, -1)
        inner_margin = 3
        fill_width = int((width - inner_margin * 2) * progress)
        if fill_width > 0:
            cv2.rectangle(
                img,
                (x + inner_margin, y + inner_margin),
                (x + inner_margin + fill_width, y + height - inner_margin),
                fill_color,
                -1,
            )
        cv2.rectangle(img, (x, y), (x + width, y + height), border_color, 2)

    def _draw_crosshair(self, img, x, y, target_entity):
        """Dibuja una mira con color y apertura según el estado del arma."""
        weapon = self.engine.weapon
        armed = weapon.esta_armada()
        charge = weapon.get_energia_carga()

        if target_entity is None:
            color = (220, 220, 220)
        elif target_entity.tipo == "malo":
            color = (80, 255, 120)
        else:
            color = (90, 120, 255)

        if armed:
            outer_radius = 18
            gap = 5
            thickness = 2
        else:
            outer_radius = int(24 - (charge * 6))
            gap = int(10 - (charge * 4))
            thickness = 2

        if weapon.debe_mostrar_destello():
            cv2.circle(img, (x, y), outer_radius + 10, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.circle(img, (x, y), outer_radius, color, 1, cv2.LINE_AA)
        cv2.line(img, (x - outer_radius, y), (x - gap, y), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x + gap, y), (x + outer_radius, y), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x, y - outer_radius), (x, y - gap), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x, y + gap), (x, y + outer_radius), color, thickness, cv2.LINE_AA)
        cv2.circle(img, (x, y), 2 if armed else 1, color, -1, cv2.LINE_AA)

    def _draw_hit_feedbacks(self, img):
        """Dibuja textos flotantes de impactos recientes."""
        now = time.time()
        remaining_feedbacks = []
        for feedback in self.hit_feedbacks:
            age = now - feedback["created_at"]
            duration = feedback["duration"]
            if age >= duration:
                continue

            remaining_feedbacks.append(feedback)
            progress = age / duration
            y_offset = int(progress * 42)
            text_y = max(28, feedback["y"] - 22 - y_offset)
            alpha = 1.0 - progress

            overlay = img.copy()
            cv2.putText(
                overlay,
                feedback["label"],
                (feedback["x"] - 18, text_y),
                cv2.FONT_HERSHEY_DUPLEX,
                0.9,
                feedback["color"],
                2,
                cv2.LINE_AA,
            )
            cv2.addWeighted(overlay, alpha, img, 1.0 - alpha, 0.0, img)

        self.hit_feedbacks = remaining_feedbacks

    def _draw_hud(self, game_img, target_entity):
        """Dibuja HUD superior, score, carga y estado del arma."""
        weapon = self.engine.weapon
        score = self.engine.get_score()
        self.display_score += (score - self.display_score) * 0.22

        if score != self.last_score_value:
            self.last_score_value = score
            self.score_pulse_until = max(self.score_pulse_until, time.time() + 0.28)

        pulse_active = time.time() < self.score_pulse_until
        panel_height = 92
        self._draw_rounded_panel(
            game_img,
            (18, 18),
            (self.width - 18, panel_height),
            fill_color=(18, 24, 34),
            border_color=(68, 94, 122),
            alpha=0.62,
        )

        score_scale = 1.4 if pulse_active else 1.2
        score_color = self.score_flash_color if pulse_active else (240, 246, 255)
        cv2.putText(
            game_img,
            "SCORE",
            (36, 48),
            cv2.FONT_HERSHEY_DUPLEX,
            0.7,
            (155, 205, 245),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            game_img,
            str(int(round(self.display_score))),
            (34, 82),
            cv2.FONT_HERSHEY_DUPLEX,
            score_scale,
            score_color,
            2,
            cv2.LINE_AA,
        )

        charge = weapon.get_energia_carga()
        charge_color = (90, 255, 140) if weapon.esta_armada() else (255, 210, 90)
        cv2.putText(
            game_img,
            "CHARGE",
            (220, 48),
            cv2.FONT_HERSHEY_DUPLEX,
            0.7,
            (155, 205, 245),
            1,
            cv2.LINE_AA,
        )
        self._draw_bar(
            game_img,
            x=220,
            y=58,
            width=220,
            height=18,
            progress=charge,
            fill_color=charge_color,
            background_color=(30, 38, 52),
            border_color=(88, 108, 132),
        )

        state_label = "READY" if weapon.esta_armada() else "CHARGING"
        state_color = (90, 255, 140) if weapon.esta_armada() else (255, 210, 90)
        cv2.putText(
            game_img,
            state_label,
            (462, 74),
            cv2.FONT_HERSHEY_DUPLEX,
            0.8,
            state_color,
            2,
            cv2.LINE_AA,
        )

        hint = "Pulgar arriba para cargar y disparar"
        cv2.putText(
            game_img,
            hint,
            (self.width - 360, 48),
            cv2.FONT_HERSHEY_DUPLEX,
            0.55,
            (196, 208, 224),
            1,
            cv2.LINE_AA,
        )

        target_label = "TARGET LOCK" if target_entity and target_entity.tipo == "malo" else "ALLY IN SIGHT" if target_entity else "NO TARGET"
        target_color = (90, 255, 140) if target_entity and target_entity.tipo == "malo" else (90, 120, 255) if target_entity else (190, 196, 210)
        cv2.putText(
            game_img,
            target_label,
            (self.width - 220, 76),
            cv2.FONT_HERSHEY_DUPLEX,
            0.72,
            target_color,
            2,
            cv2.LINE_AA,
        )

        if self.show_pistola:
            self._draw_crosshair(game_img, self.pistola_x, self.pistola_y, target_entity)

        self._draw_hit_feedbacks(game_img)

    def compose_game_frame(self, frame_count):
        """Construye un frame completo del juego sin asumir backend de ventana."""
        success, cam_img = self.camera_manager.read()
        if not success or cam_img is None:
            if frame_count == 1:
                print("[WARNING] No hay cámara disponible, usando fondo estático")
            game_img = self._compose_parallax_background()
            results = None
        else:
            cam_img = cv2.flip(cam_img, 1)
            img_rgb = cv2.cvtColor(cam_img, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)

            if self.show_background:
                game_img = self._compose_parallax_background()
            else:
                game_img = cv2.resize(
                    cam_img,
                    (self.background.shape[1], self.background.shape[0]),
                    interpolation=cv2.INTER_AREA,
                )

        if results is not None:
            _, pointer_x, pointer_y = self._process_hand_landmarks(results, cam_img)
        else:
            pointer_x = self.pistola_x
            pointer_y = self.pistola_y

        pointer = (pointer_x, pointer_y) if self.show_pistola else None
        self.engine.update(game_img, pointer=pointer)
        game_img = self.entity_renderer.render_entities(self.engine.entities, game_img)
        target_entity = self._find_entity_under_pointer(pointer_x, pointer_y) if self.show_pistola else None

        if self.show_pistola:
            game_img = self.weapon_renderer.draw(
                self.engine.weapon,
                game_img,
                self.pistola_x,
                self.pistola_y,
                size=2,
            )

        self._draw_hud(game_img, target_entity)
        self.show_pistola = False
        return self.camera_manager.resize_to_screen(game_img)

    def draw_score(self, game_img):
        """Dibuja la puntuación sobre el frame actual."""
        cv2.putText(
            game_img,
            str(self.engine.get_score()),
            (10, 70),
            cv2.FONT_HERSHEY_PLAIN,
            3,
            (255, 0, 255),
            3,
        )

    def shutdown(self):
        """Libera recursos compartidos del juego."""
        self.engine.weapon.detener_ambiente()
        self.camera_manager.release()
