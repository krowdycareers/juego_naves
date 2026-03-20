"""Loop principal alternativo usando pygame como backend de ventana/eventos."""

from __future__ import annotations

import cv2
import numpy as np

from ..audio import PygameSoundPlayer
from ..core import config
from ..game.weapon import Weapon
from .game_main import GameMain

try:
    import pygame
except ImportError:
    pygame = None


class PygameMain(GameMain):
    """Ejecuta el juego usando pygame para ventana, eventos y reloj."""

    def __init__(self, camera_index=None, background_path=None, no_interactive=False):
        if pygame is None:
            raise RuntimeError(
                "pygame no está instalado. Instala dependencias actualizadas para usar el backend pygame."
            )

        pygame.init()
        sound_player = PygameSoundPlayer(pygame_module=pygame)
        weapon = Weapon(sound_player=sound_player)
        super().__init__(
            camera_index=camera_index,
            background_path=background_path,
            no_interactive=no_interactive,
            weapon=weapon,
        )
        self._window_flags = self._resolve_window_flags()
        self.screen = pygame.display.set_mode((self.width, self.height), self._window_flags)
        pygame.display.set_caption("Messi Game")
        self.clock = pygame.time.Clock()

    def _resolve_window_flags(self):
        if config.FULLSCREEN and self.camera_manager.screen_index > 0:
            return pygame.FULLSCREEN
        return 0

    def _frame_to_surface(self, frame):
        """Convierte un frame BGR de OpenCV a una Surface de pygame."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surface = pygame.surfarray.make_surface(np.transpose(rgb_frame, (1, 0, 2)))
        if surface.get_size() != self.screen.get_size():
            surface = pygame.transform.smoothscale(surface, self.screen.get_size())
        return surface

    def _handle_pygame_events(self):
        """Procesa eventos de pygame y retorna False si se debe cerrar."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_b:
                    self.show_background = not self.show_background
                elif event.key == pygame.K_h:
                    self.show_hand_points = not self.show_hand_points

        return True

    def run(self):
        """Loop principal del juego usando pygame."""
        print(f"[DEBUG] Dimensiones pygame: {self.width}x{self.height}")
        print("[DEBUG] Iniciando loop principal pygame...")

        frame_count = 0
        running = True

        while running:
            frame_count += 1
            running = self._handle_pygame_events()
            if not running:
                break

            game_img = self._compose_game_frame(frame_count)
            surface = self._frame_to_surface(game_img)
            self.screen.blit(surface, (0, 0))
            pygame.display.flip()
            self.clock.tick(config.TARGET_FPS)

        print("[DEBUG] Limpiando pygame...")
        pygame.quit()
        self.camera_manager.release()
        print("[DEBUG] Juego finalizado")
