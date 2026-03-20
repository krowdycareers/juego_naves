"""
Weapon - Sistema de arma (pistola futurista).
Gestiona carga, disparo, efectos visuales y sonoros.
"""

import time
import math

from ..core import config
from ..audio import SystemSoundPlayer


class Weapon:
    """
    Arma futurista (pistola).
    
    Estados:
    - FIRING: Disparando
    - IDLE: En reposo
    - CHARGING: Cargando
    """

    FIRING = "firing"
    IDLE = "idle"
    CHARGING = "charging"

    def __init__(self, shot_cooldown=None, charge_time=None, sound_player=None):
        """
        Args:
            shot_cooldown: Tiempo entre disparos (None = usa config)
            charge_time: Tiempo de carga (None = usa config)
        """
        self.estado = self.IDLE
        self.ultimo_disparo = 0.0
        self.shot_cooldown = shot_cooldown or config.WEAPON_SHOT_COOLDOWN
        self.destello_hasta = 0.0
        self.sound_player = sound_player or SystemSoundPlayer()

        # Sistema de arme
        self.carga_tiempo = charge_time or config.WEAPON_CHARGE_TIME
        self.tiempo_carga_inicio = 0.0
        self.energia_carga = 0.0  # 0.0 a 1.0
        self.armada = False

    
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
        """Reproduce sonido de disparo mediante el backend configurado."""
        self.sound_player.play_shot()

    def reproducir_sonido_objetivo(self, tipo):
        """Reproduce un sonido distinto al destruir nave/astronauta."""
        self.sound_player.play_target_hit(tipo)
    
    def dibujar(self, img, x, y, size=1):
        """Mantiene compatibilidad con el render OpenCV actual."""
        from ..rendering import OpenCVWeaponRenderer

        renderer = OpenCVWeaponRenderer()
        return renderer.draw(self, img, x, y, size=size)
