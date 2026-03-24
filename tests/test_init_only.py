#!/usr/bin/env python3
"""
Test simple para validar que GameMain se inicializa correctamente.
"""

import sys
print("[TEST] 1. Iniciando test...")

try:
    print("[TEST] 2. Importando GameMain...")
    from src.ui.game_main import GameMain
    print("[TEST] 3. GameMain importado OK")
    
    print("[TEST] 4. Creando instancia GameMain...")
    game = GameMain()
    print("[TEST] 5. GameMain creado OK")
    print(f"[TEST]    - Background: {game.background.shape}")
    print(f"[TEST]    - Engine entities: {len(game.engine.entities)}")
    
    print("[TEST] 6. Test completado EXITOSAMENTE")
    sys.exit(0)
    
except Exception as e:
    print(f"[ERROR] {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
