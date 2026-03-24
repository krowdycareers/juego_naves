"""
GestorDeCamera - Maneja la captura desde cámara o pantalla.
Proporciona acceso a frames de video y gestión de resolución.
"""

import cv2
import screeninfo
import platform
import math

try:
    import mss
except ImportError:
    mss = None

try:
    import numpy as np
except ImportError:
    np = None


class CameraManager:
    """Gestiona cámara o captura de pantalla y pantalla completa.

    Soporta dos modos:
    - 'camera': Captura desde una webcam
    - 'screen': Captura de pantalla

    Ejemplo:
        manager = CameraManager(mode='camera')
        manager.create_window('Game')
        success, frame = manager.read()
        manager.release()
    """

    def __init__(self, mode='camera', cam_index=None, screen_index=0, 
                 max_cam_search=8, fullscreen=True):
        """
        Args:
            mode: 'camera' o 'screen'
            cam_index: Índice de cámara (None = automático)
            screen_index: Índice de pantalla
            max_cam_search: Máximo índice de cámara a buscar
            fullscreen: Si es True, ventana en fullscreen
        """
        self.mode = mode
        self.cam_index = cam_index
        self.screen_index = screen_index
        self.max_cam_search = max_cam_search
        self.fullscreen = fullscreen
        self.system = platform.system().lower()
        self.backend = self._preferred_backend()

        # Información de monitor
        monitors = screeninfo.get_monitors()
        if not monitors:
            raise RuntimeError("No se detectaron monitores")
        self.monitor_count = len(monitors)
        if screen_index < 0 or screen_index >= len(monitors):
            screen_index = min(max(0, screen_index), len(monitors) - 1)
        self.screen_index = screen_index
        self.monitor = monitors[screen_index]
        self.monitor_x = getattr(self.monitor, 'x', 0)
        self.monitor_y = getattr(self.monitor, 'y', 0)
        self.width = self.monitor.width
        self.height = self.monitor.height

        self.cap = None
        self.sct = None

        if self.mode == 'camera':
            self._init_camera()
        else:
            self._init_screen_capture()

    def _preferred_backend(self):
        """Retorna el backend preferido de OpenCV según el sistema."""
        if self.system == 'darwin':
            return cv2.CAP_AVFOUNDATION
        if self.system.startswith('win'):
            return cv2.CAP_DSHOW
        return cv2.CAP_V4L2

    def should_use_fullscreen(self, fullscreen=None):
        """Determina si corresponde usar pantalla completa real."""
        if fullscreen is None:
            fullscreen = self.fullscreen
        if not fullscreen:
            return False

        # En macOS y en configuraciones de una sola pantalla, fullscreen en la
        # pantalla principal es un caso valido y esperado.
        if self.system == 'darwin' or self.monitor_count <= 1:
            return True

        # Mantiene el comportamiento previo para setups multi-monitor en otros SO.
        return self.screen_index > 0

    def apply_window_mode(self, name, fullscreen=None):
        """Aplica el modo de ventana adecuado para el monitor seleccionado."""
        use_fullscreen = self.should_use_fullscreen(fullscreen)

        # Coloca la ventana en el monitor seleccionado antes de ajustar el modo.
        try:
            cv2.moveWindow(name, self.monitor_x, self.monitor_y)
        except Exception:
            pass

        if use_fullscreen:
            cv2.setWindowProperty(
                name,
                cv2.WND_PROP_FULLSCREEN,
                cv2.WINDOW_FULLSCREEN
            )
            cv2.setWindowProperty(
                name,
                cv2.WND_PROP_ASPECT_RATIO,
                cv2.WINDOW_FREERATIO
            )
            return

        cv2.setWindowProperty(
            name,
            cv2.WND_PROP_ASPECT_RATIO,
            cv2.WINDOW_FREERATIO
        )
        cv2.resizeWindow(name, self.width, self.height)

    def _init_camera(self):
        """Inicializa la captura de cámara."""
        cams = self._find_cameras(self.max_cam_search)
        if cams and self.cam_index is None:
            self.cam_index = cams[0][0]
        elif self.cam_index is None:
            self.cam_index = 0

        self.cap = self._open_capture(self.cam_index)

    def _init_screen_capture(self):
        """Inicializa la captura de pantalla."""
        if mss is None or np is None:
            raise RuntimeError(
                'mss/numpy no instalado. Instala: pip install mss numpy'
            )
        self.sct = mss.mss()
        self._mss_monitor = {
            "top": 0, 
            "left": 0, 
            "width": self.width, 
            "height": self.height
        }

    def _open_capture(self, device_id, timeout=2.0):
        """Abre un dispositivo de captura."""
        if device_id is None:
            return None
        
        cap = None
        try:
            if self.backend is not None:
                cap = cv2.VideoCapture(device_id, self.backend)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            cap = None
        
        if cap is None or not cap.isOpened():
            try:
                cap = cv2.VideoCapture(device_id)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                cap = None
        
        return cap

    def _find_cameras(self, max_index=4, device_ids=None):
        """Encuentra cámaras disponibles."""
        available = []
        if device_ids is None:
            device_ids = list(range(max_index + 1))
        
        for device_id in device_ids:
            cap = self._open_capture(device_id)
            if cap is None or not cap.isOpened():
                try:
                    if cap is not None:
                        cap.release()
                except Exception:
                    pass
                continue
            
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                available.append((device_id, w, h))
            
            try:
                cap.release()
            except Exception:
                pass
        
        return available

    def list_cameras(self):
        """Retorna lista de cámaras disponibles."""
        return self._find_cameras(self.max_cam_search)

    def list_camera_devices(self):
        """Retorna lista de dicts con info de cámaras."""
        cams = self._find_cameras(self.max_cam_search)
        return [
            {
                'id': i, 
                'name': f'Camera {i}', 
                'width': w, 
                'height': h
            } 
            for (i, w, h) in cams
        ]

    def choose_camera_grid_interactively(self, window_name='Selecciona camara'):
        """Muestra una pantalla de introducción con mosaico en vivo y permite elegir cámara.

        Controles:
        - Click izquierdo sobre una celda para seleccionar cámara.
        - Tecla numérica (0-9) para seleccionar por índice.
        - `q` o `ESC` para cancelar.
        - Flechas para navegar, ENTER para seleccionar.
        """
        if self.mode != 'camera':
            return None
        if np is None:
            return None

        # Liberar cámara actual para evitar bloquear nuevos VideoCapture.
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        opened = []
        for i in range(self.max_cam_search + 1):
            cap_t = self._open_capture(i)
            if cap_t is None or not cap_t.isOpened():
                try:
                    if cap_t is not None:
                        cap_t.release()
                except Exception:
                    pass
                continue
            ret, frame = cap_t.read()
            if not ret or frame is None:
                try:
                    cap_t.release()
                except Exception:
                    pass
                continue
            opened.append({'id': i, 'cap': cap_t, 'last_frame': frame})

        if not opened:
            return None

        selected = {'id': None}
        mouse = {'x': 0, 'y': 0, 'inside': False}
        hover = {'id': None}
        tiles = []
        selected_pos = 0
        ids = [item['id'] for item in opened]
        if self.cam_index in ids:
            selected_pos = ids.index(self.cam_index)

        def _on_mouse(event, x, y, flags, param):
            mouse['x'] = x
            mouse['y'] = y
            mouse['inside'] = True
            hover['id'] = None
            for t in tiles:
                x0, y0, x1, y1 = t['rect']
                if x0 <= x <= x1 and y0 <= y <= y1:
                    hover['id'] = t['id']
                    break
            if event == cv2.EVENT_LBUTTONDOWN and hover['id'] is not None:
                selected['id'] = hover['id']

        cv2.namedWindow("Image", cv2.WINDOW_NORMAL)
        # Poner la ventana en fullscreen
        # Evitar franjas laterales por preservación de aspect ratio de la ventana.
        cv2.setMouseCallback(window_name, _on_mouse)

        while True:
            n = len(opened)
            cols = max(1, int(math.ceil(math.sqrt(n))))
            rows = int(math.ceil(n / cols))
            header_h = 70
            gap = 10
            mosaic_w = max(640, self.width)
            mosaic_h = max(480, self.height)
            tile_w = max(160, (mosaic_w - (cols + 1) * gap) // cols)
            tile_h = max(120, (mosaic_h - header_h - (rows + 1) * gap) // rows)

            canvas = np.zeros((mosaic_h, mosaic_w, 3), dtype=np.uint8)
            cv2.putText(
                canvas,
                'Flechas+Enter | Click para elegir | Tecla numerica | ESC/q para salir',
                (16, 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (230, 230, 230),
                2
            )

            tiles = []
            for idx, item in enumerate(opened):
                ret, frame = item['cap'].read()
                if ret and frame is not None:
                    item['last_frame'] = frame
                frame = item['last_frame']
                resized = cv2.resize(frame, (tile_w, tile_h), interpolation=cv2.INTER_AREA)

                r = idx // cols
                c = idx % cols
                x0 = gap + c * (tile_w + gap)
                y0 = header_h + gap + r * (tile_h + gap)
                x1 = x0 + tile_w
                y1 = y0 + tile_h
                if y1 > mosaic_h or x1 > mosaic_w:
                    continue
                canvas[y0:y1, x0:x1] = resized

                label = f"Cam {item['id']}"
                cv2.putText(canvas, label, (x0 + 8, y0 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

                # Borde base
                border_color = (80, 80, 80)
                border_thickness = 2
                if idx == selected_pos:
                    border_color = (0, 255, 0)
                    border_thickness = 4
                    cv2.putText(
                        canvas,
                        'ENTER para seleccionar',
                        (x0 + 8, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 255, 0),
                        2
                    )

                # Hover visual: "por seleccionarlo"
                if hover['id'] == item['id']:
                    overlay = canvas[y0:y1, x0:x1].copy()
                    hover_tint = np.full_like(overlay, (40, 200, 255))
                    overlay = cv2.addWeighted(overlay, 0.78, hover_tint, 0.22, 0)
                    canvas[y0:y1, x0:x1] = overlay
                    border_color = (0, 200, 255)
                    border_thickness = max(border_thickness, 4)

                cv2.rectangle(canvas, (x0, y0), (x1, y1), border_color, border_thickness)
                tiles.append({'id': item['id'], 'rect': (x0, y0, x1, y1)})

            # Cursor "manito" dibujado
            if mouse['inside']:
                mx, my = mouse['x'], mouse['y']
                hand_color = (0, 220, 255) if hover['id'] is not None else (200, 200, 200)
                # Dedo
                cv2.line(canvas, (mx, my), (mx, my + 18), hand_color, 3)
                # Palma simple
                cv2.rectangle(canvas, (mx - 6, my + 14), (mx + 8, my + 28), hand_color, 2)

            cv2.imshow(window_name, canvas)
            key = cv2.waitKeyEx(16)
            key_low = key & 0xFF
            if key in (27, ord('q')):
                break
            if key in (10, 13):
                selected['id'] = opened[selected_pos]['id']
            elif key in (81, 2424832, 65361, 63234) or key_low in (2,):  # left
                if selected_pos % cols > 0:
                    selected_pos -= 1
            elif key in (83, 2555904, 65363, 63235) or key_low in (3,):  # right
                if selected_pos % cols < cols - 1 and selected_pos + 1 < len(opened):
                    selected_pos += 1
            elif key in (82, 2490368, 65362, 63232) or key_low in (0,):  # up
                if selected_pos - cols >= 0:
                    selected_pos -= cols
            elif key in (84, 2621440, 65364, 63233) or key_low in (1,):  # down
                if selected_pos + cols < len(opened):
                    selected_pos += cols
            elif ord('0') <= key <= ord('9'):
                key_idx = key - ord('0')
                if any(item['id'] == key_idx for item in opened):
                    selected_pos = ids.index(key_idx)
                    selected['id'] = key_idx
            if selected['id'] is not None:
                break

        selected_id = selected['id']
        selected_cap = None
        for item in opened:
            if selected_id is not None and item['id'] == selected_id:
                selected_cap = item['cap']
            else:
                try:
                    item['cap'].release()
                except Exception:
                    pass

        cv2.destroyWindow(window_name)

        if selected_id is None:
            return None

        self.cap = selected_cap
        self.cam_index = selected_id
        return selected_id

    def read(self):
        """Lee un frame."""
        if self.mode == 'camera':
            if self.cap is None:
                return False, None
            ret, frame = self.cap.read()
            return ret, frame
        else:
            if self.sct is None:
                return False, None
            frame = self.sct.grab(self._mss_monitor)
            frame_cv = np.array(frame)
            frame_cv = cv2.cvtColor(frame_cv, cv2.COLOR_RGBA2BGR)
            return True, frame_cv

    def create_window(self, name='Window'):
        """Crea una ventana."""
        cv2.namedWindow(name, cv2.WINDOW_NORMAL)
        self.apply_window_mode(name)

    def resize_to_screen(self, frame):
        """Redimensiona un frame al tamaño de la pantalla."""
        return cv2.resize(
            frame,
            (self.width, self.height),
            interpolation=cv2.INTER_AREA
        )

    def release(self):
        """Libera recursos."""
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        if self.sct is not None:
            try:
                self.sct.__exit__(None, None, None)
            except Exception:
                pass
