import time
import math
import cv2
import numpy as np
import platform
import subprocess
import threading


class Pistola:
    """Gestiona el estado de la pistola basado en la dirección del pulgar.
    
    Estados:
    - DISPARANDO: pulgar apunta hacia arriba
    - NO_DISPARANDO: pulgar apunta hacia abajo
    - DESCARGANDO: en proceso de carga/arme
    
    Los landmarks del pulgar son:
    - 2: thumb_mcp (base del pulgar)
    - 3: thumb_ip (articulación media)
    - 4: thumb_tip (punta del pulgar)
    """
    
    DISPARANDO = "dispensando"
    NO_DISPARANDO = "no_disparando"
    DESCARGANDO = "descargando"
    
    def __init__(self, shot_cooldown=0.12, carga_tiempo=0.25):
        self.estado = self.NO_DISPARANDO
        self.ultimo_disparo = 0.0
        self.shot_cooldown = shot_cooldown
        self.destello_hasta = 0.0
        
        # Sistema de arme
        self.carga_tiempo = carga_tiempo  # Tiempo de carga en segundos
        self.tiempo_carga_inicio = 0.0
        self.energia_carga = 0.0  # 0.0 a 1.0
        self.armada = False  # Si la pistola está lista para disparar
    
    def actualizar_estado(self, landmarks):
        """Actualiza el estado basado en la dirección del pulgar usando ángulo.
        Incluye sistema de arme y carga.
        
        Args:
            landmarks (dict): Diccionario con los landmarks {id: (x, y)}
                             Necesita: 2 (thumb_mcp), 3 (thumb_ip), 4 (thumb_tip)
        
        Returns:
            bool: True si ocurrió un disparo, False en caso contrario
        """
        if not all(key in landmarks for key in [2, 3, 4]):
            return False
        
        x2, y2 = landmarks[2]  # thumb_mcp (azul - base)
        x4, y4 = landmarks[4]  # thumb_tip (rojo - punta)
        
        # Calcular ángulo entre azul (base) y rojo (punta)
        dx = x4 - x2
        dy = y4 - y2
        
        angulo_rad = math.atan2(dy, dx)
        angulo_deg = math.degrees(angulo_rad)
        
        # Normalizar a rango 0-360
        if angulo_deg < 0:
            angulo_deg += 360
        
        # Rango para disparar: 220 a 260 grados (pulgar hacia arriba)
        rango_disparo_min = 220
        rango_disparo_max = 280
        pulgar_arriba = rango_disparo_min <= angulo_deg <= rango_disparo_max
        
        now = time.time()
        
        # === Lógica de ARME - La pistola debe estar cargada para disparar ===
        if pulgar_arriba:
            # Si el pulgar está arriba, comenzar a cargar/armar
            if self.energia_carga < 1.0:
                if self.tiempo_carga_inicio == 0:
                    self.tiempo_carga_inicio = now
                
                # Calcular progreso de carga
                tiempo_transcurrido = now - self.tiempo_carga_inicio
                self.energia_carga = min(1.0, tiempo_transcurrido / self.carga_tiempo)
                self.armada = self.energia_carga >= 1.0
        else:
            # Pulgar no está arriba, resetear carga
            self.tiempo_carga_inicio = 0
            self.energia_carga = max(0, self.energia_carga - 0.05)  # Descargar lentamente
            self.armada = False
        
        # === Disparo solo ocurre si está ARMADA ===
        disparo_generado = False
        if pulgar_arriba and self.armada and now >= self.ultimo_disparo + self.shot_cooldown:
            disparo_generado = True
            self.ultimo_disparo = now
            self.destello_hasta = now + 0.15  # Destello visible por 150ms
            self.energia_carga = 0.0  # Descargar la pistola después de disparar
            self.tiempo_carga_inicio = 0
            self.armada = False
        
        return disparo_generado
    
    def debe_mostrar_destello(self):
        """Retorna True si debe mostrarse el destello de disparo."""
        return time.time() < self.destello_hasta
    
    def get_energia_carga(self):
        """Retorna el nivel de carga de la pistola (0.0 a 1.0)."""
        return self.energia_carga
    
    def esta_armada(self):
        """Retorna True si la pistola está completamente armada y lista."""
        return self.armada
    
    def esta_disparando(self):
        """Retorna el estado actual de la pistola."""
        return self.estado == self.DISPARANDO
    
    def get_debug_info(self, landmarks):
        """Retorna información de debug sobre la posición del pulgar con ángulo."""
        if not all(key in landmarks for key in [2, 3, 4]):
            return "Sin landmarks del pulgar"
        
        x2, y2 = landmarks[2]  # thumb_mcp (azul - base)
        x3, y3 = landmarks[3]  # thumb_ip (verde - medio)
        x4, y4 = landmarks[4]  # thumb_tip (rojo - punta)
        
        # Calcular ángulo entre azul (2 - base) y rojo (4 - punta)
        # Vector desde azul a rojo
        dx = x4 - x2
        dy = y4 - y2
        
        # Ángulo en radianes (atan2 retorna -π a π)
        angulo_rad = math.atan2(dy, dx)
        # Convertir a grados (-180 a 180)
        angulo_deg = math.degrees(angulo_rad)
        
        # Normalizar a rango 0-360
        if angulo_deg < 0:
            angulo_deg += 360
        
        # Diferencias Y
        diferencia_mcp_tip = y2 - y4
        
        margin = 20
        pulgar_arriba = y4 < (y2 - margin)
        pulgar_abajo = y4 > (y2 + margin)
        
        info = f"Ángulo(azul→rojo): {angulo_deg:6.1f}° | Δy: {diferencia_mcp_tip:3.0f} | "
        if pulgar_arriba:
            info += "↑ ARRIBA"
        elif pulgar_abajo:
            info += "↓ ABAJO"
        else:
            info += "→ NEUTRAL"
        
        info += f" | Estado: {self.estado}"
        
        return info
    
    def reproducir_sonido(self):
        """Reproduce sonido de disparo sin bloquear el loop principal."""
        def _play_shot_sound():
            try:
                system = platform.system().lower()
                if system == 'darwin':
                    subprocess.Popen(
                        ['afplay', '/System/Library/Sounds/Pop.aiff'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                elif system.startswith('win'):
                    import winsound
                    winsound.PlaySound('SystemAsterisk', winsound.SND_ALIAS | winsound.SND_ASYNC)
                else:
                    print('\a', end='', flush=True)
            except Exception:
                pass
        
        threading.Thread(target=_play_shot_sound, daemon=True).start()
    
    def dibujar(self, img, x, y, size=1):
        """Dibuja la pistola futurista en la imagen.
        
        Args:
            img: Imagen de OpenCV donde dibujar
            x, y: Coordenadas de la mira
            size: Escala del arma
        """
        pistola = np.zeros((100, 85, 3), dtype=np.uint8)
        
        # Colores realistas (basados en imagen sci-fi)
        color_negro = (20, 20, 25)
        color_gris_oscuro = (45, 45, 50)
        color_gris_medio = (65, 65, 75)
        color_gris_claro = (100, 105, 115)
        
        # === CAÑÓN CIRCULAR PRINCIPAL ===
        cv2.circle(pistola, (42, 18), 14, color_negro, -1)
        cv2.circle(pistola, (42, 18), 12, color_gris_oscuro, -1)
        cv2.circle(pistola, (42, 18), 10, color_gris_medio, -1)
        
        # Energía del cañón (cambia con carga)
        energia_color_r = int(50 + 105 * self.energia_carga)
        energia_color_g = int(150 + 105 * self.energia_carga)
        energia_color_b = 220
        cv2.circle(pistola, (42, 18), 7, (energia_color_b, energia_color_g, energia_color_r), -1)
        
        # Centro brillante del cañón
        cv2.circle(pistola, (42, 18), 4, (220, 220, 200), -1)
        
        # Líneas de energía radiantes
        for i in range(8):
            angle = (360 / 8) * i
            rad = math.radians(angle)
            x1 = int(42 + math.cos(rad) * 8)
            y1 = int(18 + math.sin(rad) * 8)
            x2 = int(42 + math.cos(rad) * 14)
            y2 = int(18 + math.sin(rad) * 14)
            cv2.line(pistola, (x1, y1), (x2, y2), (energia_color_b, energia_color_g, energia_color_r), 1)
        
        # === ESTRUCTURA FRONTAL ===
        cv2.rectangle(pistola, (28, 8), (33, 38), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (51, 8), (56, 38), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (29, 10), (32, 36), color_gris_medio, -1)
        cv2.rectangle(pistola, (52, 10), (55, 36), color_gris_medio, -1)
        
        # Placa superior
        cv2.rectangle(pistola, (33, 6), (51, 12), color_gris_medio, -1)
        cv2.rectangle(pistola, (35, 7), (39, 11), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (41, 7), (44, 11), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (47, 7), (51, 11), color_gris_oscuro, -1)
        
        # === SISTEMA DE RECARGA ===
        cv2.rectangle(pistola, (30, 38), (54, 50), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (32, 40), (52, 48), color_gris_medio, -1)
        for i in range(32, 52, 3):
            cv2.line(pistola, (i, 40), (i, 48), color_gris_oscuro, 1)
        
        # === EMPUÑADURA ===
        cv2.rectangle(pistola, (34, 50), (50, 98), color_gris_oscuro, -1)
        cv2.rectangle(pistola, (36, 52), (48, 96), color_gris_medio, -1)
        for i in range(52, 96, 2):
            cv2.line(pistola, (36, i), (48, i), color_negro, 1)
        
        # Guardamontes
        cv2.ellipse(pistola, (42, 62), (11, 16), 0, 0, 180, color_gris_oscuro, -1)
        
        # === DISPARADOR ===
        cv2.rectangle(pistola, (39, 55), (45, 70), color_gris_medio, -1)
        cv2.rectangle(pistola, (40, 57), (44, 68), color_gris_claro, -1)
        
        # === INDICADOR DE ESTADO ===
        if self.armada:
            cv2.circle(pistola, (30, 42), 2, (0, 255, 0), -1)
        else:
            cv2.circle(pistola, (30, 42), 2, (0, 0, 255), -1)

        # Escalar
        pistola = cv2.resize(
            pistola,
            (int(pistola.shape[1] * size), int(pistola.shape[0] * size)),
            interpolation=cv2.INTER_LINEAR
        )

        sight_x = int(42 * size)
        sight_y = 0

        h, w = pistola.shape[:2]
        img_h, img_w = img.shape[:2]

        x0 = int(x - sight_x)
        y0 = int(y - sight_y)

        if x0 >= img_w or y0 >= img_h or x0 + w <= 0 or y0 + h <= 0:
            return img

        pistola_crop = pistola.copy()
        if x0 + w > img_w:
            pistola_crop = pistola_crop[:, :img_w - x0]
            w = pistola_crop.shape[1]
        if y0 + h > img_h:
            pistola_crop = pistola_crop[:img_h - y0, :]
            h = pistola_crop.shape[0]

        if x0 < 0:
            pistola_crop = pistola_crop[:, -x0:]
            w = pistola_crop.shape[1]
            x0 = 0
        if y0 < 0:
            pistola_crop = pistola_crop[-y0:, :]
            h = pistola_crop.shape[0]
            y0 = 0

        if h > 0 and w > 0:
            roi = img[y0:y0+h, x0:x0+w]
            gray = cv2.cvtColor(pistola_crop, cv2.COLOR_BGR2GRAY)
            mask = gray > 5
            roi[mask] = pistola_crop[mask]

        # === MIRA TRANSPARENTE ===
        if self.debe_mostrar_destello():
            cv2.circle(img, (x, y), 3, (0, 255, 255), -1)
            cv2.circle(img, (x, y), 2, (255, 255, 100), -1)
            cv2.line(img, (x - 8, y), (x + 8, y), (0, 255, 255), 1)
            cv2.line(img, (x, y - 8), (x, y + 8), (0, 255, 255), 1)

        # === EFECTOS DE DESTELLO ===
        if self.debe_mostrar_destello():
            flash_intensity = (math.sin(time.time() * 30) + 1) / 2
            flash_intensity = max(0.5, flash_intensity)
            
            flash_r1 = max(12, int(16 * size * flash_intensity))
            color1 = (int(0 * flash_intensity), int(165 * flash_intensity), int(255 * flash_intensity))
            cv2.circle(img, (x, y), flash_r1, color1, -1)
            
            flash_r2 = max(6, int(8 * size * flash_intensity))
            cv2.circle(img, (x, y), flash_r2, (255, 255, 255), -1)
            
            num_rays = 8
            for i in range(num_rays):
                ang = (360 / num_rays) * i + (time.time() * 60 % 360)
                rad = math.radians(ang)
                flash_length = max(15, int(22 * size))
                x2 = int(x + math.cos(rad) * flash_length)
                y2 = int(y + math.sin(rad) * flash_length)
                
                ray_color = (int(0 * flash_intensity), int(200 * flash_intensity), int(255 * flash_intensity))
                cv2.line(img, (x, y), (x2, y2), ray_color, max(1, int(2 * size)))
            
            flash_r3 = max(20, int(28 * size * flash_intensity))
            ring_color = (0, int(100 * flash_intensity), int(200 * flash_intensity))
            cv2.circle(img, (x, y), flash_r3, ring_color, max(1, int(2 * size)))

        return img
