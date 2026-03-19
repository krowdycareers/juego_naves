#!/usr/bin/env python3
"""
Script simple para tester el renderizado del juego sin complicaciones.
"""

import cv2
import numpy as np
from src.ui.game_main import GameMain

print("[TEST] Iniciando test de renderizado...")

# Crear instancia del juego
game = GameMain(no_interactive=True)
print(f"[TEST] GameMain inicializado")
print(f"[TEST] Background shape: {game.background.shape}")
print(f"[TEST] Background min/max values: {game.background.min()}/{game.background.max()}")

# Generar algunos frames para test
game_img = game.background.copy()
game.engine.update(game_img)
game_img = game.engine.render_entities(game_img, None)

print(f"[TEST] Primer frame renderizado: shape={game_img.shape}, min/max={game_img.min()}/{game_img.max()}")

# Mostrar en ventana
cv2.namedWindow("Test Game Render", cv2.WINDOW_NORMAL)
cv2.imshow("Test Game Render", game_img)
print("[TEST] Mostrando imagen en ventana...presione cualquier tecla")

# Esperar a que el usuario presione una tecla
key = cv2.waitKey(10000)  # 10 segundo timeout
print(f"[TEST] Tecla presionada: {key}")

cv2.destroyAllWindows()
print("[TEST] Completado")
