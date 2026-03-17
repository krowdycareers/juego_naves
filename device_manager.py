import cv2
import screeninfo
import platform
import math

try:
    import mss
except Exception:
    mss = None

try:
    import numpy as np
except Exception:
    np = None


class DeviceManager:
    """Gestiona cámara o captura de pantalla y fullscreen.

    Uso:
        dm = DeviceManager(mode='camera')  # o mode='screen'
        dm.create_window('Image')
        ok, frame = dm.read()
        dm.release()
    """

    def __init__(self, mode='camera', cam_index=None, screen_index=0, max_cam_search=8, fullscreen=True):
        self.mode = mode
        # cam_index puede ser int (index) o str (device id backend-specific)
        self.cam_index = cam_index
        self.screen_index = screen_index
        self.max_cam_search = max_cam_search
        self.fullscreen = fullscreen
        self.backend = self._preferred_backend()

        # Monitor info
        self.monitor = screeninfo.get_monitors()[screen_index]
        self.width = self.monitor.width
        self.height = self.monitor.height

        self.cap = None
        self.sct = None

        if self.mode == 'camera':
            # abrir cámara (si cam_index es None, seleccionar primera encontrada)
            cams = self._find_cameras(self.max_cam_search)
            if cams:
                if self.cam_index is None:
                    # si hay varias, escoger la primera disponible
                    self.cam_index = cams[0][0]
            else:
                # fallback a 0
                if self.cam_index is None:
                    self.cam_index = 0

            self.cap = self._open_capture(self.cam_index)
        else:
            # screen mode
            if mss is None or np is None:
                raise RuntimeError('mss/numpy no está instalado; instala `mss` y `numpy` para captura de pantalla')
            self.sct = mss.mss()
            self._mss_monitor = {"top": 0, "left": 0, "width": self.width, "height": self.height}

    def _preferred_backend(self):
        system = platform.system().lower()
        if system == 'darwin':
            return cv2.CAP_AVFOUNDATION
        if system.startswith('win'):
            return cv2.CAP_DSHOW
        return cv2.CAP_V4L2

    def _open_capture(self, device_id, timeout=2.0):
        if device_id is None:
            return None
        cap = None
        try:
            if self.backend is not None:
                cap = cv2.VideoCapture(device_id, self.backend)
                # Establecer timeout y reducir buffer
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
        disponible = []
        if device_ids is None:
            device_ids = list(range(max_index + 1))
        for device_id in device_ids:
            cap_t = self._open_capture(device_id)
            if cap_t is None or not cap_t.isOpened():
                try:
                    if cap_t is not None:
                        cap_t.release()
                except Exception:
                    pass
                continue
            ret, frame = cap_t.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                disponible.append((device_id, w, h))
            try:
                cap_t.release()
            except Exception:
                pass
        return disponible

    def _get_camera_names(self, max_index=8):
        names = {}
        for i in range(max_index + 1):
            names[i] = f"Camera {i}"
        return names

    def list_cameras(self):
        return self._find_cameras(self.max_cam_search)

    def camera_names(self):
        return self._get_camera_names(self.max_cam_search)

    def list_camera_devices(self):
        """Devuelve lista de dicts con id/name/width/height (id usable por OpenCV)."""
        cams = self._find_cameras(self.max_cam_search)
        return [{'id': i, 'name': f'Camera {i}', 'width': w, 'height': h} for (i, w, h) in cams]

    def choose_camera_interactively(self, window_name='Camera Preview'):
        """Muestra una vista previa secuencial de las cámaras detectadas.

        Controles mientras se muestra cada cámara:
        - Presiona `s` para seleccionar la cámara mostrada.
        - Presiona `n` o cualquier otra tecla para pasar a la siguiente.
        - Presiona `q` o `ESC` para cancelar y no cambiar la cámara actual.

        Al seleccionar, reabre `self.cap` con el índice elegido y devuelve ese índice.
        """
        cams = self.list_camera_devices()
        names = {d['id']: d['name'] for d in cams}
        if not cams:
            return None

        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        for d in cams:
            idx = d['id']
            cap_t = self._open_capture(idx)
            ret, frame = cap_t.read()
            if not ret or frame is None:
                cap_t.release()
                continue

            # Escalar la vista previa para que quepa en pantalla si es necesario
            try:
                maxw = min(640, frame.shape[1])
                scale = maxw / frame.shape[1]
                if scale < 1.0:
                    frame = cv2.resize(frame, (int(frame.shape[1]*scale), int(frame.shape[0]*scale)), interpolation=cv2.INTER_AREA)
            except Exception:
                pass

            label = f"Index {idx} - {names.get(idx, f'Camera {idx}')}"
            cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
            cv2.imshow(window_name, frame)

            key = cv2.waitKey(0) & 0xFF
            if key == ord('s'):
                # seleccionar esta cámara
                try:
                    # liberar cap anterior si existe
                    if self.cap is not None:
                        try:
                            self.cap.release()
                        except Exception:
                            pass
                    # Reuse the preview VideoCapture to avoid remapping issues
                    self.cap = cap_t
                    self.cam_index = idx
                except Exception:
                    pass
                cv2.destroyWindow(window_name)
                return idx
            if key in (27, ord('q')):
                # ESC o q -> cancelar
                cv2.destroyWindow(window_name)
                # release the preview capture for this index since we're not selecting it
                try:
                    cap_t.release()
                except Exception:
                    pass
                return None
            # cualquier otra tecla -> siguiente: release preview cap and continue
            try:
                cap_t.release()
            except Exception:
                pass

        cv2.destroyWindow(window_name)
        return None

    def choose_camera_grid_interactively(self, window_name='Selecciona camara'):
        """Muestra una pantalla de introducción con mosaico en vivo y permite elegir cámara.

        Controles:
        - Click izquierdo sobre una celda para seleccionar cámara.
        - Tecla numérica (0-9) para seleccionar por índice.
        - `q` o `ESC` para cancelar.
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

        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
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

            # Cursor "manito" dibujado (OpenCV no cambia cursor del sistema de forma portable).
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
        """Devuelve (success, frame) en BGR."""
        if self.mode == 'camera':
            if self.cap is None:
                return False, None
            ret, frame = self.cap.read()
            return ret, frame
        else:
            if self.sct is None:
                return False, None
            sct_img = self.sct.grab(self._mss_monitor)
            frame = np.array(sct_img)
            # BGRA -> BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            return True, frame

    def release(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        if self.sct is not None:
            try:
                self.sct.close()
            except Exception:
                pass

    def create_window(self, name='Image'):
        cv2.namedWindow(name, cv2.WINDOW_NORMAL)
        if self.fullscreen:
            cv2.setWindowProperty(name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    def resize_to_screen(self, frame):
        try:
            return cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_CUBIC)
        except Exception:
            return frame
