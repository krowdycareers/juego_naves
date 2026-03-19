#!/usr/bin/env python3
"""
Script para probar el selector de cámaras.
Ejecutar: python test_camera_selector.py
Presionar: ESC para salir sin seleccionar, o click/número para seleccionar cámara
"""

import sys
import time
from src.ui.game_main import GameMain

print("[TEST] Creando GameMain (mostrará selector de cámaras)...")
try:
    game = GameMain(no_interactive=False)  # ← Mostrar selector
    print("[TEST] GameMain inicializado correctamente")
    print("[TEST] Iniciando juego...")
    
    # Ejecutar el juego por 30 segundos o hasta que el usuario presione ESC
    game.run()
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[TEST] Completado")
