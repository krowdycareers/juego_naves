"""Lógica compartida del ciclo principal del juego, independiente del backend UI."""

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
    """Base compartida para backends de ventana como OpenCV y pygame."""

    def __init__(self, camera_index=None, background_path=None, no_interactive=False, weapon=None):
        self.camera_manager = CameraManager(
            mode=config.CAMERA_MODE,
            cam_index=camera_index,
            screen_index=config.SCREEN_INDEX,
            max_cam_search=config.CAMERA_MAX_SEARCH,
            fullscreen=config.FULLSCREEN,
        )

        if not no_interactive:
            print("[DEBUG] Verificando disponibilidad de cámaras para selector...")
            try:
                available_cams = self.camera_manager.list_cameras()
                if available_cams:
                    print(f"[DEBUG] Encontradas {len(available_cams)} cámaras, mostrando selector...")
                    selected_cam = self.camera_manager.choose_camera_grid_interactively(
                        window_name="Selección de Cámara"
                    )
                    if selected_cam is not None:
                        print(f"[DEBUG] Cámara seleccionada: {selected_cam}")
                    else:
                        print("[DEBUG] Selección cancelada, usando cámara por defecto")
                else:
                    print("[DEBUG] No hay cámaras disponibles, saltando selector")
            except Exception as exc:
                print(f"[WARNING] Error en selector de cámaras: {exc}")

        self.width = self.camera_manager.width
        self.height = self.camera_manager.height
        self.background = self._load_background(background_path)

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
        self.entity_renderer = OpenCVEntityRenderer()
        self.weapon_renderer = OpenCVWeaponRenderer()

        self.show_background = True
        self.show_hand_points = False
        self.last_frame_time = time.time()
        self.pistola_x = 0
        self.pistola_y = 0
        self.show_pistola = False
        print("[DEBUG] BaseGameApp inicializado completamente")

    def _load_background(self, bg_path=None):
        """Carga la imagen de fondo por defecto o una personalizada."""
        if bg_path:
            bg = cv2.imread(bg_path)
            if bg is not None:
                result = cv2.resize(bg, (self.width, self.height), interpolation=cv2.INTER_AREA)
                print(f"[DEBUG] Fondo cargado desde: {bg_path}, shape={result.shape}")
                return result

        for fallback_path in config.FALLBACK_BACKGROUND_PATHS:
            bg = cv2.imread(str(fallback_path))
            if bg is not None:
                result = cv2.resize(bg, (self.width, self.height), interpolation=cv2.INTER_AREA)
                print(f"[DEBUG] Fondo cargado desde fallback: {fallback_path}, shape={result.shape}")
                return result

        print("[DEBUG] No se encontró imagen de fondo, usando fondo negro")
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)

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
                    self.engine.weapon.reproducir_sonido()
                    self.engine.process_shot(pointer_x, pointer_y)

                self.show_pistola = True
                self.pistola_x = pointer_x
                self.pistola_y = pointer_y

        return firing, pointer_x, pointer_y

    def compose_game_frame(self, frame_count):
        """Construye un frame completo del juego sin asumir backend de ventana."""
        success, cam_img = self.camera_manager.read()
        if not success or cam_img is None:
            if frame_count == 1:
                print("[WARNING] No hay cámara disponible, usando fondo estático")
            game_img = self.background.copy()
            results = None
        else:
            cam_img = cv2.flip(cam_img, 1)
            img_rgb = cv2.cvtColor(cam_img, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)

            if self.show_background:
                game_img = self.background.copy()
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

        if self.show_pistola:
            game_img = self.weapon_renderer.draw(
                self.engine.weapon,
                game_img,
                self.pistola_x,
                self.pistola_y,
                size=2,
            )

        self.draw_score(game_img)
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
        self.camera_manager.release()

