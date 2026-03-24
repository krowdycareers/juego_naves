"""
Configuración centralizada del proyecto Messi.
Define constantes, parámetros del juego y configuraciones del sistema.
"""

import os
from pathlib import Path

# ===== Rutas =====
PROJECT_ROOT = Path(__file__).parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
SFX_DIR = ASSETS_DIR / "sfx"
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
UI_BACKEND = "pygame"

# ===== Juego - Parámetros generales =====
TARGET_FPS = 60
FRAME_TIME = 1.0 / TARGET_FPS

# ===== Naves/Astronautas =====
NUM_ENTITIES = 10
ENTITY_SIZE = 20
ENTITY_SPAWN_ATTEMPTS = 1000
PLAYER_SPRITE_SCALE = 0.27
ENEMY_SPRITE_SCALE = 0.25
COLLISION_RADIUS_FACTOR = 0.72
SHOT_RADIUS_FACTOR = 1.1

# ===== Arma (Pistola) =====
WEAPON_SHOT_COOLDOWN = 0.12
WEAPON_CHARGE_TIME = 0.25
WEAPON_FLASH_DURATION = 0.15
WEAPON_SPRITE_SCALE = 0.24
WEAPON_FIRE_ANIMATION_FPS = 18
WEAPON_SIGHT_ANCHOR_X = 0.50
WEAPON_SIGHT_ANCHOR_Y = 0.13
WEAPON_RETICLE_HIT_PADDING = 18
HITBOX_PADDING = 10

# ===== Thumb/Pulgar para disparo =====
THUMB_FIRE_RANGE_MIN = 220  # grados
THUMB_FIRE_RANGE_MAX = 280  # grados

# ===== Detección de objetos - Lógica de huida =====
ENTITY_ESCAPE_DETECTION_RANGE = 260
ENTITY_ESCAPE_BASE_SPEED_MIN = 6.0
ENTITY_ESCAPE_BASE_SPEED_MAX = 14.0
ENTITY_ESCAPE_VELOCITY_BLEND = 0.35

# ===== Colisiones =====
COLLISION_HEIGHT_THRESHOLD = 0.55
COLLISION_EXPLOSION_FRAMES = 10
COLLISION_RESPAWN_ITERATIONS_MIN = 1
COLLISION_RESPAWN_ITERATIONS_MAX = 10

# ===== Disparo (targeting) =====
SHOT_TARGET_RADIUS = 34
SHOT_SCORE_ENEMY = 2  # Al destruir nave (malo)
SHOT_SCORE_PENALTY_FRIENDLY = 1  # Al destruir astronauta (bueno)

# ===== Escala de profundidad (perspectiva) =====
DEPTH_MIN_SCALE = 0.68
DEPTH_MAX_SCALE = 1.12
DEPTH_STEPS = 0

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
BACKGROUND_PARALLAX_ENABLED = False
BACKGROUND_PARALLAX_BASE_SPEED_X = 4.0
BACKGROUND_PARALLAX_BASE_SPEED_Y = 14.0
BACKGROUND_CROP_TOP = 0.0
BACKGROUND_CROP_BOTTOM = 0.30
BACKGROUND_COLOR_GRADE_ENABLED = True
BACKGROUND_BRIGHTNESS = 0.88
BACKGROUND_CONTRAST = 1.08
BACKGROUND_BLUE_GAIN = 1.14
BACKGROUND_GREEN_GAIN = 1.04
BACKGROUND_RED_GAIN = 0.84
BACKGROUND_HAZE_ALPHA = 0.12
BACKGROUND_PARALLAX_LAYERS = (
    {
        "name": "far",
        "count": 48,
        "alpha": 0.22,
        "radius_min": 1,
        "radius_max": 2,
        "trail": 0.0,
        "color": (170, 150, 120),
        "speed_x": 0.25,
        "speed_y": 0.45,
    },
    {
        "name": "mid",
        "count": 34,
        "alpha": 0.32,
        "radius_min": 1,
        "radius_max": 3,
        "trail": 0.45,
        "color": (210, 200, 170),
        "speed_x": -0.55,
        "speed_y": 0.95,
    },
    {
        "name": "near",
        "count": 22,
        "alpha": 0.42,
        "radius_min": 2,
        "radius_max": 4,
        "trail": 0.9,
        "color": (255, 245, 220),
        "speed_x": 0.8,
        "speed_y": 1.55,
    },
)

# ===== Configuración de usuario =====
USER_CONFIG_PATH = os.path.expanduser("~/.messi_config.json")
