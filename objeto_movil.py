import math


class circulo:
    def __init__(self, x, y, size, vx=0, vy=0, tipo='bueno'):
        """Inicializa un cuadrado en movimiento."""
        self.x = x
        self.y = y
        self.size = size
        self.vx = vx
        self.vy = vy
        self.tipo = tipo
        self.color = (255, 0, 0) if tipo == 'bueno' else (0, 0, 255)
        self.activo = True
        self.iteraciones_para_reaparecer = 0

    def ocultar(self, iteraciones=10):
        self.activo = False
        self.iteraciones_para_reaparecer = max(1, int(iteraciones))

    def actualizar_reaparicion(self):
        if self.activo:
            return False
        self.iteraciones_para_reaparecer -= 1
        if self.iteraciones_para_reaparecer <= 0:
            self.activo = True
            self.iteraciones_para_reaparecer = 0
            return True
        return False

    def mover(self, ancho, alto):
        """Mueve el cuadrado en base a su velocidad y rebota en los bordes del área rectangular."""
        if not self.activo:
            return
        self.x += self.vx
        self.y += self.vy

        # Rebote en bordes laterales
        if self.x < 0:
            self.x = 0  # Ajustar la posición dentro del área
            self.vx *= -1  # Invertir dirección en X
        elif self.x + self.size > ancho:
            self.x = ancho - self.size
            self.vx *= -1

        # Rebote en bordes superior e inferior
        if self.y < 0:
            self.y = 0
            self.vy *= -1  # Invertir dirección en Y
        elif self.y + self.size > alto:
            self.y = alto - self.size
            self.vy *= -1

    def detectar_colision(self, otro):
        """Detecta colisión real entre círculos usando distancia cuadrada (sin sqrt)."""
        if not self.activo or not otro.activo:
            return False
        # Optimización: usar distancia cuadrada para evitar sqrt innecesario
        dx = self.x - otro.x
        dy = self.y - otro.y
        dist_squared = dx * dx + dy * dy
        radio_sum = (self.size + otro.size) / 2
        radius_squared = radio_sum * radio_sum
        return dist_squared <= radius_squared

    def rebotar(self, otro):
        """Cambia la dirección en caso de colisión con otro cuadrado."""
        if self.detectar_colision(otro):
            if abs(self.x - otro.x) > abs(self.y - otro.y):
                self.vx *= -1  # Rebote en X
            else:
                self.vy *= -1  # Rebote en Y
