"""Punto de entrada principal del juego usando pygame como ventana y eventos."""

from __future__ import annotations

import cv2
import math
import numpy as np

from ..audio import PygameSoundPlayer
from ..core import config
from ..core.camera_manager import CameraManager
from ..game.weapon import Weapon
from .base_game import BaseGameApp

try:
    import pygame
except ImportError:
    pygame = None


class GameMain(BaseGameApp):
    """Aplicación principal del juego con pygame como backend único de UI."""

    WINDOW_TITLE = "Messi Game"

    def __init__(self):
        if pygame is None:
            raise RuntimeError(
                "pygame no está instalado. Instala las dependencias del proyecto para ejecutar el juego."
            )

        pygame.init()
        camera_index = self._resolve_camera_index()
        sound_player = PygameSoundPlayer(pygame_module=pygame)
        weapon = Weapon(sound_player=sound_player)
        super().__init__(camera_index=camera_index, weapon=weapon)

        self._window_flags = self._resolve_window_flags()
        self.screen = pygame.display.set_mode((self.width, self.height), self._window_flags)
        pygame.display.set_caption(self.WINDOW_TITLE)
        self.clock = pygame.time.Clock()

    def _resolve_camera_index(self):
        """Permite elegir cámara solo cuando hay más de una disponible."""
        if config.CAMERA_MODE != "camera":
            return None

        probe_manager = None
        try:
            probe_manager = self._build_probe_camera_manager()
            devices = probe_manager.list_camera_devices()
            default_id = probe_manager.cam_index
        except Exception as exc:
            print(f"[WARNING] No se pudo inspeccionar cámaras: {exc}")
            devices = []
            default_id = None
        finally:
            if probe_manager is not None:
                probe_manager.release()

        if not devices:
            return None
        if len(devices) == 1:
            return devices[0]["id"]

        return self._show_camera_selector(devices, default_id=default_id)

    def _build_probe_camera_manager(self):
        """Crea un CameraManager temporal para listar cámaras disponibles."""
        return CameraManager(
            mode=config.CAMERA_MODE,
            screen_index=config.SCREEN_INDEX,
            max_cam_search=config.CAMERA_MAX_SEARCH,
            fullscreen=config.FULLSCREEN,
        )

    def _show_camera_selector(self, devices, default_id=None):
        """Muestra un selector con previews en vivo de cada cámara."""
        selector_width = 1120
        selector_height = 720
        screen = pygame.display.set_mode((selector_width, selector_height))
        pygame.display.set_caption("Seleccion de camara")

        title_font = pygame.font.SysFont("arial", 34, bold=True)
        body_font = pygame.font.SysFont("arial", 24)
        hint_font = pygame.font.SysFont("arial", 18)
        badge_font = pygame.font.SysFont("arial", 16, bold=True)
        clock = pygame.time.Clock()
        preview_streams = self._create_camera_preview_streams(devices)

        selected_index = 0
        if default_id is not None:
            for index, device in enumerate(devices):
                if device["id"] == default_id:
                    selected_index = index
                    break

        option_rects = []
        running = True
        chosen_id = devices[selected_index]["id"]

        try:
            while running:
                mouse_pos = pygame.mouse.get_pos()
                option_rects = []
                columns = 2 if len(devices) > 1 else 1
                rows = int(math.ceil(len(devices) / float(columns)))
                grid_x = 60
                grid_y = 168
                grid_gap = 20
                card_width = (selector_width - (grid_x * 2) - (grid_gap * (columns - 1))) // columns
                card_height = min(240, max(190, (selector_height - grid_y - 60 - (grid_gap * max(0, rows - 1))) // max(1, rows)))

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        break

                    if event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_ESCAPE, pygame.K_q):
                            running = False
                            break
                        if event.key in (pygame.K_LEFT, pygame.K_a) and selected_index > 0:
                            selected_index -= 1
                        elif event.key in (pygame.K_RIGHT, pygame.K_d) and selected_index < len(devices) - 1:
                            selected_index += 1
                        elif event.key in (pygame.K_UP, pygame.K_w) and selected_index - columns >= 0:
                            selected_index -= columns
                        elif event.key in (pygame.K_DOWN, pygame.K_s) and selected_index + columns < len(devices):
                            selected_index += columns
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            chosen_id = devices[selected_index]["id"]
                            running = False
                            break
                        elif pygame.K_0 <= event.key <= pygame.K_9:
                            pressed = event.key - pygame.K_0
                            for index, device in enumerate(devices):
                                if device["id"] == pressed:
                                    selected_index = index
                                    chosen_id = device["id"]
                                    running = False
                                    break

                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for index, rect in enumerate(option_rects):
                            if rect.collidepoint(event.pos):
                                selected_index = index
                                chosen_id = devices[index]["id"]
                                running = False
                                break

                screen.fill((11, 14, 22))
                pygame.draw.rect(screen, (24, 32, 44), (32, 32, selector_width - 64, selector_height - 64), border_radius=24)
                pygame.draw.rect(screen, (78, 108, 145), (32, 32, selector_width - 64, selector_height - 64), 2, border_radius=24)

                title_surface = title_font.render("Selecciona una camara", True, (236, 244, 255))
                hint_surface = hint_font.render(
                    "Previews en vivo. Flechas o click para elegir. Enter confirma. ESC usa la camara por defecto.",
                    True,
                    (170, 184, 206),
                )
                screen.blit(title_surface, (60, 70))
                screen.blit(hint_surface, (60, 114))

                hovered_index = None
                for index, device in enumerate(devices):
                    row = index // columns
                    col = index % columns
                    rect = pygame.Rect(
                        grid_x + col * (card_width + grid_gap),
                        grid_y + row * (card_height + grid_gap),
                        card_width,
                        card_height,
                    )
                    option_rects.append(rect)
                    is_hovered = rect.collidepoint(mouse_pos)
                    is_selected = index == selected_index
                    if is_hovered:
                        hovered_index = index

                    fill = (33, 43, 59) if is_selected else (22, 28, 39)
                    border = (98, 232, 160) if is_selected else (74, 90, 112)
                    if is_hovered and not is_selected:
                        fill = (29, 38, 52)
                        border = (102, 172, 226)

                    pygame.draw.rect(screen, fill, rect, border_radius=18)
                    pygame.draw.rect(screen, border, rect, 2, border_radius=18)

                    preview_rect = pygame.Rect(rect.x + 14, rect.y + 14, rect.width - 28, rect.height - 78)
                    preview_surface = self._read_camera_preview_surface(preview_streams.get(device["id"]), preview_rect.size)
                    screen.blit(preview_surface, preview_rect.topleft)
                    pygame.draw.rect(screen, (60, 74, 94), preview_rect, 1, border_radius=12)

                    label_surface = body_font.render(f"Camara {device['id']}", True, (240, 246, 255))
                    detail_surface = hint_font.render(f"{device['width']}x{device['height']}", True, (170, 184, 206))
                    screen.blit(label_surface, (rect.x + 16, rect.bottom - 52))
                    screen.blit(detail_surface, (rect.x + 16, rect.bottom - 28))

                    badge_rect = pygame.Rect(rect.right - 116, rect.y + 16, 96, 28)
                    badge_fill = (24, 78, 56) if is_selected else (31, 43, 58)
                    badge_text = "ACTIVA" if is_selected else "DISPONIBLE"
                    pygame.draw.rect(screen, badge_fill, badge_rect, border_radius=999)
                    badge_surface = badge_font.render(badge_text, True, (229, 244, 235))
                    badge_pos = badge_surface.get_rect(center=badge_rect.center)
                    screen.blit(badge_surface, badge_pos)

                if hovered_index is not None:
                    selected_index = hovered_index

                pygame.display.flip()
                clock.tick(24)
        finally:
            self._release_camera_preview_streams(preview_streams)

        pygame.event.clear()
        return chosen_id

    def _create_camera_preview_streams(self, devices):
        """Abre capturas temporales para mostrar previews en vivo en el selector."""
        preview_streams = {}
        probe_manager = self._build_probe_camera_manager()
        try:
            for device in devices:
                capture = probe_manager._open_capture(device["id"])
                if capture is not None and capture.isOpened():
                    preview_streams[device["id"]] = {"capture": capture, "last_frame": None}
                elif capture is not None:
                    capture.release()
        finally:
            probe_manager.cap = None
            probe_manager.release()
        return preview_streams

    def _read_camera_preview_surface(self, stream, size):
        """Lee el último frame disponible y lo convierte a una surface de pygame."""
        width, height = size
        if stream is None:
            return self._build_unavailable_preview(width, height, "Sin senal")

        capture = stream["capture"]
        ret, frame = capture.read()
        if ret and frame is not None:
            stream["last_frame"] = frame
        frame = stream["last_frame"]
        if frame is None:
            return self._build_unavailable_preview(width, height, "Cargando...")

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_height, frame_width = rgb_frame.shape[:2]
        scale = min(width / max(1, frame_width), height / max(1, frame_height))
        resized_size = (
            max(1, int(frame_width * scale)),
            max(1, int(frame_height * scale)),
        )
        surface = pygame.Surface((width, height))
        surface.fill((8, 10, 16))

        preview = pygame.surfarray.make_surface(np.transpose(rgb_frame, (1, 0, 2)))
        preview = pygame.transform.smoothscale(preview, resized_size)
        offset_x = (width - resized_size[0]) // 2
        offset_y = (height - resized_size[1]) // 2
        surface.blit(preview, (offset_x, offset_y))
        return surface

    def _build_unavailable_preview(self, width, height, message):
        """Genera una preview placeholder cuando la cámara aún no entrega imagen."""
        surface = pygame.Surface((width, height))
        surface.fill((12, 16, 24))
        pygame.draw.rect(surface, (55, 68, 84), (0, 0, width, height), 1, border_radius=12)
        font = pygame.font.SysFont("arial", 22)
        label = font.render(message, True, (168, 180, 198))
        label_pos = label.get_rect(center=(width // 2, height // 2))
        surface.blit(label, label_pos)
        return surface

    def _release_camera_preview_streams(self, preview_streams):
        """Libera las capturas temporales usadas por el selector."""
        for stream in preview_streams.values():
            capture = stream.get("capture")
            if capture is not None:
                try:
                    capture.release()
                except Exception:
                    pass

    def _resolve_window_flags(self):
        """Calcula flags de ventana según la configuración de pantalla."""
        if self.camera_manager.should_use_fullscreen(config.FULLSCREEN):
            return pygame.FULLSCREEN
        return 0

    def _frame_to_surface(self, frame):
        """Convierte un frame BGR de OpenCV a una Surface de pygame."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surface = pygame.surfarray.make_surface(np.transpose(rgb_frame, (1, 0, 2)))
        if surface.get_size() != self.screen.get_size():
            surface = pygame.transform.smoothscale(surface, self.screen.get_size())
        return surface

    def _handle_events(self):
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
            running = self._handle_events()
            if not running:
                break

            game_img = self.compose_game_frame(frame_count)
            surface = self._frame_to_surface(game_img)
            self.screen.blit(surface, (0, 0))
            pygame.display.flip()
            self.clock.tick(config.TARGET_FPS)

        print("[DEBUG] Limpiando pygame...")
        pygame.quit()
        self.shutdown()
        print("[DEBUG] Juego finalizado")


def main():
    """Función principal del juego."""
    game = GameMain()
    game.run()


if __name__ == '__main__':
    main()
