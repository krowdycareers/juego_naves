"""
game_main - Interfaz y loop principal del juego.
Maneja detección de manos, rendering y entrada del usuario.
"""

import cv2
import time
import argparse

from ..core import config
from .base_game import BaseGameApp


class GameMain(BaseGameApp):
    """Runner del juego usando OpenCV como backend de ventana."""

    def _handle_opencv_key(self, key):
        """Procesa una tecla de OpenCV y retorna False si se debe cerrar."""
        if key == ord('b') or key == ord('B'):
            self.show_background = not self.show_background
            print(f"[DEBUG] Toggle background: {self.show_background}")
            return True
        if key == ord('h') or key == ord('H'):
            self.show_hand_points = not self.show_hand_points
            return True
        if key == 27:
            print("[DEBUG] ESC presionado, saliendo...")
            return False
        return True

    def run(self):
        """Loop principal del juego."""
        print("[DEBUG] Creando ventana de juego...")
        self.camera_manager.create_window("Messi Game")

        print(f"[DEBUG] Dimensiones: {self.width}x{self.height}")
        print("[DEBUG] Iniciando loop principal...")
        
        frame_count = 0
        running = True
        while running:
            frame_count += 1
            game_img = self.compose_game_frame(frame_count)

            cv2.imshow("Messi Game", game_img)

            current_time = time.time()
            elapsed = current_time - self.last_frame_time
            if elapsed < config.FRAME_TIME:
                wait_ms = max(1, int((config.FRAME_TIME - elapsed) * 1000))
                key = cv2.waitKey(wait_ms)
            else:
                key = cv2.waitKey(1)

            self.last_frame_time = time.time()
            running = self._handle_opencv_key(key)

        print("[DEBUG] Limpiando...")
        cv2.destroyAllWindows()
        self.shutdown()
        print("[DEBUG] Juego finalizado")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Messi - Juego interactivo")
    parser.add_argument('--cam', type=int, help='Índice de cámara')
    parser.add_argument('--bg', type=str, help='Ruta de imagen de fondo')
    parser.add_argument('--no-interactive', action='store_true', help='Sin selector de cámara')
    parser.add_argument(
        '--backend',
        choices=['opencv', 'pygame'],
        default=config.UI_BACKEND,
        help='Backend de ventana/render a utilizar'
    )
    args = parser.parse_args()

    if args.backend == 'pygame':
        from .pygame_main import PygameMain

        game = PygameMain(
            camera_index=args.cam,
            background_path=args.bg,
            no_interactive=args.no_interactive
        )
    else:
        game = GameMain(
            camera_index=args.cam,
            background_path=args.bg,
            no_interactive=args.no_interactive
        )

    game.run()


if __name__ == '__main__':
    main()
