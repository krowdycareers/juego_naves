"""
game_main - Interfaz y loop principal del juego.
Maneja detección de manos, rendering y entrada del usuario.
"""

import cv2
import mediapipe as mp
import time
import os
import json
import argparse
import numpy as np

from ..core.camera_manager import CameraManager
from ..core import config
from ..game.game_engine import GameEngine
from ..game.weapon import Weapon


class GameMain:
    """Controlador principal del juego."""

    def __init__(self, camera_index=None, background_path=None, no_interactive=False):
        """
        Args:
            camera_index: Índice de cámara (None = automático)
            background_path: Ruta del fondo (None = automático)
            no_interactive: Si True, no mostrar selector de cámara
        """
        # Inicializar cámara
        self.camera_manager = CameraManager(
            mode=config.CAMERA_MODE,
            cam_index=camera_index,
            max_cam_search=config.CAMERA_MAX_SEARCH,
            fullscreen=config.FULLSCREEN
        )
        
        # Mostrar selector de cámaras si no es automático
        if not no_interactive:
            print("[DEBUG] Verificando disponibilidad de cámaras para selector...")
            try:
                # Primero verificar si hay cámaras disponibles
                available_cams = self.camera_manager.list_cameras()
                if available_cams:
                    print(f"[DEBUG] Encontradas {len(available_cams)} cámaras, mostrando selector...")
                    selected_cam = self.camera_manager.choose_camera_grid_interactively(
                        window_name='Selección de Cámara'
                    )
                    if selected_cam is not None:
                        print(f"[DEBUG] Cámara seleccionada: {selected_cam}")
                    else:
                        print("[DEBUG] Selección cancelada, usando cámara por defecto")
                else:
                    print("[DEBUG] No hay cámaras disponibles, saltando selector")
            except Exception as e:
                print(f"[WARNING] Error en selector de cámaras: {e}")
        
        self.width = self.camera_manager.width
        self.height = self.camera_manager.height

        # Cargar fondo
        self.background = self._load_background(background_path)

        # Inicializar MediaPipe
        mp_hands = mp.solutions.hands
        print("[DEBUG] Inicializando MediaPipe...")
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        print("[DEBUG] MediaPipe inicializado")

        # Inicializar motor de juego
        print("[DEBUG] Inicializando GameEngine...")
        self.engine = GameEngine(self.width, self.height)
        print("[DEBUG] GameEngine inicializado")

        # Estado de la UI
        self.show_background = True
        self.show_hand_points = False
        self.last_frame_time = time.time()
        self.pistola_x = 0
        self.pistola_y = 0
        self.show_pistola = False
        print("[DEBUG] GameMain inicializado completamente")

    def _load_background(self, bg_path=None):
        """Carga la imagen de fondo."""
        if bg_path:
            bg = cv2.imread(bg_path)
            if bg is not None:
                result = cv2.resize(bg, (self.width, self.height), interpolation=cv2.INTER_AREA)
                print(f"[DEBUG] Fondo cargado desde: {bg_path}, shape={result.shape}")
                return result

        # Intentar rutas por defecto
        for fallback_path in config.FALLBACK_BACKGROUND_PATHS:
            bg = cv2.imread(str(fallback_path))
            if bg is not None:
                result = cv2.resize(bg, (self.width, self.height), interpolation=cv2.INTER_AREA)
                print(f"[DEBUG] Fondo cargado desde fallback: {fallback_path}, shape={result.shape}")
                return result

        # Si no encontró, retornar negro
        print(f"[DEBUG] No se encontró imagen de fondo, usando fondo negro")
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def _process_hand_landmarks(self, results, cam_img):
        """
        Procesa los landmarks de la mano.
        
        Returns:
            (firing: bool, pointer_x: int, pointer_y: int)
        """
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

            # Verificar si tenemos los landmarks necesarios para disparar
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

    def run(self):
        """Loop principal del juego."""
        print("[DEBUG] Creando ventana de juego...")
        cv2.namedWindow("Messi Game", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Messi Game", self.width, self.height)

        print(f"[DEBUG] Dimensiones: {self.width}x{self.height}")
        print("[DEBUG] Iniciando loop principal...")
        
        frame_count = 0
        running = True
        while running:
            frame_count += 1
            
            success, cam_img = self.camera_manager.read()
            if not success or cam_img is None:
                # Sin cámara: simplemente mostrar el background
                if frame_count == 1:
                    print(f"[WARNING] No hay cámara disponible, usando fondo estático")
                game_img = self.background.copy()
                results = None
            else:
                cam_img = cv2.flip(cam_img, 1)
                img_rgb = cv2.cvtColor(cam_img, cv2.COLOR_BGR2RGB)
                results = self.hands.process(img_rgb)

                # Preparar imagen del juego
                if self.show_background:
                    game_img = self.background.copy()
                else:
                    game_img = cv2.resize(
                        cam_img,
                        (self.background.shape[1], self.background.shape[0]),
                        interpolation=cv2.INTER_AREA
                    )

            # Procesar mano y detectar disparo (si hay detección)
            if results is not None:
                firing, pointer_x, pointer_y = self._process_hand_landmarks(results, cam_img if 'cam_img' in locals() else None)
            else:
                firing = False
                pointer_x = self.pistola_x
                pointer_y = self.pistola_y

            # Preparar apuntador para huida
            apuntador = (pointer_x, pointer_y) if self.show_pistola else None

            # Actualizar motor de juego (con apuntador para huida)
            self.engine.update(game_img, pointer=apuntador)
            game_img = self.engine.render_entities(game_img)

            # Dibujar pistola
            if self.show_pistola:
                game_img = self.engine.weapon.dibujar(game_img, self.pistola_x, self.pistola_y, 2)

            # Dibujar puntuación
            cv2.putText(
                game_img,
                str(self.engine.get_score()),
                (10, 70),
                cv2.FONT_HERSHEY_PLAIN,
                3,
                (255, 0, 255),
                3
            )

            # Mostrar en ventana (sin redimensionar extra)
            cv2.imshow("Messi Game", game_img)

            # Control de FPS
            current_time = time.time()
            elapsed = current_time - self.last_frame_time
            if elapsed < config.FRAME_TIME:
                wait_ms = max(1, int((config.FRAME_TIME - elapsed) * 1000))
                key = cv2.waitKey(wait_ms)
            else:
                key = cv2.waitKey(1)

            self.last_frame_time = time.time()

            # Procesar entrada
            if key == ord('b') or key == ord('B'):
                self.show_background = not self.show_background
                print(f"[DEBUG] Toggle background: {self.show_background}")
            elif key == ord('h') or key == ord('H'):
                self.show_hand_points = not self.show_hand_points
            elif key == 27:  # ESC
                print("[DEBUG] ESC presionado, saliendo...")
                running = False

            self.show_pistola = False

        print("[DEBUG] Limpiando...")
        cv2.destroyAllWindows()
        self.camera_manager.release()
        print("[DEBUG] Juego finalizado")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Messi - Juego interactivo")
    parser.add_argument('--cam', type=int, help='Índice de cámara')
    parser.add_argument('--bg', type=str, help='Ruta de imagen de fondo')
    parser.add_argument('--no-interactive', action='store_true', help='Sin selector de cámara')
    args = parser.parse_args()

    game = GameMain(
        camera_index=args.cam,
        background_path=args.bg,
        no_interactive=args.no_interactive
    )
    game.run()


if __name__ == '__main__':
    main()
