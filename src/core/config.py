"""
Configuración centralizada del proyecto Messi.
Define constantes, parámetros del juego y configuraciones del sistema.
"""

import os
from pathlib import Path

# ===== Rutas =====
PROJECT_ROOT = Path(__file__).parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
CONFIG_DIR = PROJECT_ROOT / ".config"
CONFIG_DIR.mkdir(exist_ok=True)

# ===== Cámara =====
CAMERA_MODE = "camera"  # "camera" o "screen"
CAMERA_MAX_SEARCH = 8
CAMERA_DEFAULT_INDEX = 0
CAMERA_BUFFER_SIZE = 1

# ===== Pantalla =====
FULLSCREEN = True
SCREEN_INDEX = 1

# ===== Juego - Parámetros generales =====
TARGET_FPS = 30
FRAME_TIME = 1.0 / TARGET_FPS

# ===== Naves/Astronautas =====
NUM_ENTITIES = 10
ENTITY_SIZE = 20
ENTITY_SPAWN_ATTEMPTS = 1000

# ===== Arma (Pistola) =====
WEAPON_SHOT_COOLDOWN = 0.12
WEAPON_CHARGE_TIME = 0.25
WEAPON_FLASH_DURATION = 0.15

# ===== Thumb/Pulgar para disparo =====
THUMB_FIRE_RANGE_MIN = 220  # grados
THUMB_FIRE_RANGE_MAX = 280  # grados

# ===== Detección de objetos - Lógica de huida =====
ENTITY_ESCAPE_DETECTION_RANGE = 260
ENTITY_ESCAPE_BASE_SPEED_MIN = 6.0
ENTITY_ESCAPE_BASE_SPEED_MAX = 14.0
ENTITY_ESCAPE_VELOCITY_BLEND = 0.35

# ===== Colisiones =====
COLLISION_HEIGHT_THRESHOLD = 0.75
COLLISION_EXPLOSION_FRAMES = 10
COLLISION_RESPAWN_ITERATIONS_MIN = 1
COLLISION_RESPAWN_ITERATIONS_MAX = 10

# ===== Disparo (targeting) =====
SHOT_TARGET_RADIUS = 30
SHOT_SCORE_ENEMY = 2  # Al destruir nave (malo)
SHOT_SCORE_PENALTY_FRIENDLY = 1  # Al destruir astronauta (bueno)

# ===== Escala de profundidad (perspectiva) =====
DEPTH_MIN_SCALE = 0.55
DEPTH_MAX_SCALE = 1.35
DEPTH_STEPS = 4

# ===== Efectos visuales - Humo =====
SMOKE_EFFECT_SCALE_THRESHOLD = 0.7
SMOKE_EFFECT_LAYERS = 3
SMOKE_EFFECT_ALPHA_BASE = 0.18

# ===== Background =====
BACKGROUND_PATH = ASSETS_DIR / "imagen_fondo.jpg"
FALLBACK_BACKGROUND_PATHS = [
    ASSETS_DIR / "imagen_fondo.jpg",
    PROJECT_ROOT / "background.jpg",
    PROJECT_ROOT / "background.png",
    PROJECT_ROOT / "fondo.jpg",
    PROJECT_ROOT / "fondo.png",
]

# ===== Configuración de usuario =====
USER_CONFIG_PATH = os.path.expanduser("~/.messi_config.json")
