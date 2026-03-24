"""
GestorDeCamera - Maneja la captura desde cámara o pantalla.
Proporciona acceso a frames de video y gestión de resolución.
"""

import cv2
import screeninfo
import platform

try:
    import mss
except ImportError:
    mss = None

try:
    import numpy as np
except ImportError:
    np = None


class CameraManager:
    """Gestiona cámara o captura de pantalla para alimentar el loop del juego.

    Soporta dos modos:
    - 'camera': Captura desde una webcam
    - 'screen': Captura de pantalla
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
