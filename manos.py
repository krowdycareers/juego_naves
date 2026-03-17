import cv2
import mediapipe as mp
import time
import numpy as np
import screeninfo
import random
import math
import platform
import subprocess
import threading
from objeto_movil import circulo
from gun_hand import Pistola

from device_manager import DeviceManager
import os
import json
import argparse



def dibujar_nave_roja(img, x, y, escala=1.0):
    cx, cy = int(x), int(y)
    body_w = max(46, int(72 * escala))
    body_h = max(18, int(24 * escala))
    dome_w = max(22, int(38 * escala))
    dome_h = max(14, int(22 * escala))
    blink_phase = time.time() * 8.0

    # Halo inferior suave para dar efecto de nave
    for i in range(3):
        alpha_h = 0.17 - (i * 0.05)
        halo = img.copy()
        cv2.ellipse(
            halo,
            (cx, cy + int(10 * escala)),
            (max(8, int((body_w * 0.38) + i * 6)), max(6, int((body_h * 0.35) + i * 5))),
            0,
            0,
            360,
            (0, 0, 120),
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.addWeighted(halo, max(0.0, alpha_h), img, 1.0 - max(0.0, alpha_h), 0, img)

    # Cuerpo principal
    cv2.ellipse(
        img,
        (cx, cy),
        (body_w // 2, body_h // 2),
        0,
        0,
        360,
        (20, 20, 170),
        -1,
        lineType=cv2.LINE_AA,
    )
    cv2.ellipse(
        img,
        (cx, cy + int(2 * escala)),
        (body_w // 2, max(5, int(body_h * 0.24))),
        0,
        0,
        180,
        (0, 0, 255),
        2,
        lineType=cv2.LINE_AA,
    )

    # Cúpula
    cv2.ellipse(
        img,
        (cx, cy - int(body_h * 0.45)),
        (dome_w // 2, dome_h // 2),
        0,
        180,
        360,
        (50, 80, 255),
        -1,
        lineType=cv2.LINE_AA,
    )

    # Ventanas
    win_count = 5
    for i in range(win_count):
        wx = int(cx - body_w * 0.3 + i * (body_w * 0.15))
        wy = int(cy - body_h * 0.12)
        cv2.circle(img, (wx, wy), max(2, int(3 * escala)), (180, 220, 255), -1, lineType=cv2.LINE_AA)

    # Luces del aro
    light_count = 8
    for i in range(light_count):
        t = (2 * math.pi / light_count) * i
        lx = int(cx + math.cos(t) * (body_w * 0.42))
        ly = int(cy + math.sin(t) * (body_h * 0.20))
        pulse = 0.45 + 0.55 * max(0.0, math.sin(blink_phase + i * 0.8))
        light_color = (
            int(120 + 110 * pulse),
            int(120 + 110 * pulse),
            int(200 + 55 * pulse),
        )
        if pulse > 0.8:
            glow = img.copy()
            cv2.circle(glow, (lx, ly), max(3, int(5 * escala)), light_color, -1, lineType=cv2.LINE_AA)
            cv2.addWeighted(glow, 0.18, img, 0.82, 0, img)
        cv2.circle(img, (lx, ly), max(1, int(2 * escala)), light_color, -1, lineType=cv2.LINE_AA)


def dibujar_astronauta_azul(img, x, y, escala=1.0):
    cx, cy = int(x), int(y)
    suit_white = (245, 242, 238)
    suit_shadow = (210, 205, 220)
    visor_dark = (35, 18, 70)
    visor_glow = (120, 80, 200)
    blue = (235, 170, 60)
    blue_dark = (200, 120, 35)
    gold = (60, 180, 245)

    # Sombra bajo el personaje para separarlo del fondo.
    shadow = img.copy()
    cv2.ellipse(
        shadow,
        (cx, cy + int(24 * escala)),
        (max(10, int(22 * escala)), max(4, int(6 * escala))),
        0,
        0,
        360,
        (120, 110, 160),
        -1,
        lineType=cv2.LINE_AA,
    )
    cv2.addWeighted(shadow, 0.25, img, 0.75, 0, img)

    # Mochila
    cv2.rectangle(
        img,
        (cx + int(10 * escala), cy - int(2 * escala)),
        (cx + int(20 * escala), cy + int(14 * escala)),
        suit_shadow,
        -1,
    )

    # Casco
    cv2.circle(img, (cx, cy - int(10 * escala)), max(14, int(18 * escala)), suit_white, -1, lineType=cv2.LINE_AA)
    cv2.ellipse(
        img,
        (cx - int(2 * escala), cy - int(10 * escala)),
        (max(10, int(12 * escala)), max(12, int(14 * escala))),
        -8,
        0,
        360,
        visor_dark,
        -1,
        lineType=cv2.LINE_AA,
    )
    cv2.ellipse(
        img,
        (cx - int(7 * escala), cy - int(16 * escala)),
        (max(2, int(3 * escala)), max(4, int(5 * escala))),
        25,
        0,
        360,
        visor_glow,
        -1,
        lineType=cv2.LINE_AA,
    )
    cv2.ellipse(
        img,
        (cx + int(1 * escala), cy - int(7 * escala)),
        (max(5, int(7 * escala)), max(3, int(4 * escala))),
        0,
        15,
        165,
        (235, 210, 255),
        max(1, int(2 * escala)),
        lineType=cv2.LINE_AA,
    )
    cv2.circle(img, (cx - int(4 * escala), cy - int(10 * escala)), max(1, int(1.6 * escala)), (235, 210, 255), -1, lineType=cv2.LINE_AA)
    cv2.circle(img, (cx + int(6 * escala), cy - int(10 * escala)), max(1, int(1.6 * escala)), (235, 210, 255), -1, lineType=cv2.LINE_AA)
    cv2.circle(img, (cx + int(14 * escala), cy - int(8 * escala)), max(3, int(4 * escala)), suit_shadow, -1, lineType=cv2.LINE_AA)

    # Torso
    cv2.ellipse(
        img,
        (cx, cy + int(10 * escala)),
        (max(12, int(16 * escala)), max(10, int(13 * escala))),
        -8,
        0,
        360,
        suit_white,
        -1,
        lineType=cv2.LINE_AA,
    )
    cv2.rectangle(
        img,
        (cx - int(8 * escala), cy + int(7 * escala)),
        (cx + int(8 * escala), cy + int(12 * escala)),
        blue,
        -1,
    )
    cv2.rectangle(
        img,
        (cx - int(5 * escala), cy + int(4 * escala)),
        (cx + int(5 * escala), cy + int(11 * escala)),
        suit_shadow,
        -1,
    )
    cv2.circle(img, (cx - int(2 * escala), cy + int(8 * escala)), max(1, int(2 * escala)), (0, 0, 255), -1, lineType=cv2.LINE_AA)
    cv2.circle(img, (cx + int(2 * escala), cy + int(8 * escala)), max(1, int(2 * escala)), (0, 200, 0), -1, lineType=cv2.LINE_AA)

    # Brazos
    cv2.ellipse(img, (cx - int(16 * escala), cy + int(6 * escala)), (max(4, int(6 * escala)), max(7, int(9 * escala))), 40, 0, 360, suit_white, -1, lineType=cv2.LINE_AA)
    cv2.ellipse(img, (cx + int(16 * escala), cy + int(10 * escala)), (max(4, int(6 * escala)), max(7, int(9 * escala))), -35, 0, 360, suit_white, -1, lineType=cv2.LINE_AA)
    cv2.circle(img, (cx - int(24 * escala), cy + int(9 * escala)), max(4, int(5 * escala)), gold, -1, lineType=cv2.LINE_AA)
    cv2.circle(img, (cx + int(23 * escala), cy + int(14 * escala)), max(4, int(5 * escala)), gold, -1, lineType=cv2.LINE_AA)

    # Piernas
    cv2.ellipse(img, (cx - int(8 * escala), cy + int(26 * escala)), (max(5, int(7 * escala)), max(9, int(12 * escala))), 25, 0, 360, suit_white, -1, lineType=cv2.LINE_AA)
    cv2.ellipse(img, (cx + int(8 * escala), cy + int(24 * escala)), (max(5, int(7 * escala)), max(9, int(12 * escala))), -30, 0, 360, suit_white, -1, lineType=cv2.LINE_AA)
    cv2.ellipse(img, (cx - int(10 * escala), cy + int(30 * escala)), (max(5, int(7 * escala)), max(3, int(5 * escala))), 15, 0, 360, blue, -1, lineType=cv2.LINE_AA)
    cv2.ellipse(img, (cx + int(10 * escala), cy + int(28 * escala)), (max(5, int(7 * escala)), max(3, int(5 * escala))), -20, 0, 360, blue, -1, lineType=cv2.LINE_AA)
    cv2.ellipse(img, (cx - int(13 * escala), cy + int(38 * escala)), (max(5, int(7 * escala)), max(4, int(6 * escala))), 20, 0, 360, gold, -1, lineType=cv2.LINE_AA)
    cv2.ellipse(img, (cx + int(13 * escala), cy + int(35 * escala)), (max(5, int(7 * escala)), max(4, int(6 * escala))), -20, 0, 360, gold, -1, lineType=cv2.LINE_AA)

    # Acentos azules
    cv2.ellipse(img, (cx - int(12 * escala), cy + int(14 * escala)), (max(3, int(4 * escala)), max(3, int(5 * escala))), 35, 0, 360, blue_dark, 2, lineType=cv2.LINE_AA)
    cv2.ellipse(img, (cx + int(12 * escala), cy + int(18 * escala)), (max(3, int(4 * escala)), max(3, int(5 * escala))), -35, 0, 360, blue_dark, 2, lineType=cv2.LINE_AA)


def generar_circulos(num_cuadrados, ancho, alto, cuadrado_size):
    circulos = []
    intentos_max = 1000  # Evita bucles infinitos si el área está muy llena

    for _ in range(num_cuadrados):
        for _ in range(intentos_max):
            # Generar una posición aleatoria dentro del área rectangular
            x = random.randint(0, ancho - cuadrado_size)
            y = random.randint(0, alto - cuadrado_size)
            tipo = random.choice(['bueno', 'malo'])
            
            # Crear el cuadrado temporalmente
            nuevo_cuadrado = circulo(x, y, cuadrado_size,
                                           vx=10,
                                           vy=10,
                                           tipo=tipo)

            # Verificar si colisiona con los cuadrados existentes
            colisiona = any(nuevo_cuadrado.detectar_colision(c) for c in circulos)

            if not colisiona:
                circulos.append(nuevo_cuadrado)
                break  # Si encontramos un buen lugar, salimos del bucle

    return circulos

def pintar_circulos(circulos, img):
    HEIGHT, WIDTH = img.shape[0:2]

    for c in circulos:
        reaparecio = c.actualizar_reaparicion()
        if reaparecio:
            c.x = random.randint(0, max(0, WIDTH - c.size))
            c.y = random.randint(0, max(0, HEIGHT - c.size))

    for i in range(len(circulos)):
            for j in range(i + 1, len(circulos)):
                circulos[i].rebotar(circulos[j])
                    
    for circulo in circulos:
        if not circulo.activo:
            continue
        circulo.mover( WIDTH, HEIGHT)
        if circulo.tipo == 'malo':
            dibujar_nave_roja(img, circulo.x, circulo.y, escala=0.85)
        else:
            dibujar_astronauta_azul(img, circulo.x, circulo.y, escala=0.9)

    return img


def procesar_disparo(circulos, x_mira, y_mira, puntaje):
    radio_objetivo = 30
    for c in circulos:
        if not c.activo:
            continue
        if math.hypot(c.x - x_mira, c.y - y_mira) <= radio_objetivo:
            if c.tipo == 'malo':
                puntaje += 2
            else:
                puntaje -= 1
            c.ocultar(random.randint(1, 10))
            break
    return puntaje

# Parsear argumentos de línea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--cam', type=int, help='Forzar índice de cámara OpenCV y saltar selección interactiva')
parser.add_argument('--reset-camera', action='store_true', help='Borrar la configuración guardada de cámara')
parser.add_argument('--no-interactive', action='store_true', help='No abrir selección interactiva en mosaico (usar configuración o primera cámara)')
parser.add_argument('--bg', type=str, default='assets/imagen_fondo.jpg', help='Ruta de imagen de fondo para el juego')
args = parser.parse_args()

# Leer configuración guardada (si existe) para fijar el índice de la cámara
config_path = os.path.expanduser('~/.messi_config.json')
saved_cam = None
if args.reset_camera and os.path.exists(config_path):
    try:
        os.remove(config_path)
    except Exception:
        pass

if os.path.exists(config_path):
    try:
        with open(config_path, 'r') as f:
            cfg = json.load(f)
            saved_cam = cfg.get('cam_index')
    except Exception:
        saved_cam = None

# Si se pasa --cam, se usa y tiene prioridad
if args.cam is not None:
    use_cam = args.cam
elif saved_cam is not None:
    use_cam = saved_cam
else:
    use_cam = None

# Inicializar DeviceManager (modo 'camera' por defecto). Puedes pasar mode='screen' si quieres captura de pantalla.
dm = DeviceManager(mode='camera', cam_index=use_cam)
width, height = dm.width, dm.height

# Mostrar cámaras detectadas con nombres opcionalmente
cams = dm.list_cameras()
names = dm.camera_names()
combined = [(i, w, h, names.get(i, f"Camera {i}")) for (i, w, h) in cams]
print("Cámaras detectadas (id, width, height, name):", combined)

# Si hay cámaras, mostrar pantalla de introducción en mosaico para elegir.
if cams:
    sel = None
    if not args.no_interactive:
        print("Abriendo pantalla de introducción de cámaras. Haz click en la cámara o presiona su número.")
        sel = dm.choose_camera_grid_interactively(window_name='Seleccion de Camara')

    if sel is not None:
        print(f"Cámara seleccionada: {sel}")
        # dm.choose_camera_grid_interactively ya deja abierta la cámara seleccionada en dm.cap
        width, height = dm.width, dm.height
        try:
            with open(config_path, 'w') as f:
                json.dump({'cam_index': sel}, f)
        except Exception:
            pass
    else:
        fallback_cam = use_cam if use_cam is not None else cams[0][0]
        dm.release()
        dm = DeviceManager(mode='camera', cam_index=fallback_cam)
        print(f"Usando cámara por defecto: {fallback_cam}")
else:
    print("No se detectaron cámaras. Revisa permisos del sistema y que ninguna app esté usando la cámara.")
    raise SystemExit(1)

print(screeninfo.get_monitors())

mpHands = mp.solutions.hands
hands = mpHands.Hands(static_image_mode=False,
                      max_num_hands=2,
                      min_detection_confidence=0.5,
                      min_tracking_confidence=0.5)
mpDraw = mp.solutions.drawing_utils

circulos = generar_circulos(5, width, height, 20)

# Cargar fondo de juego para ocultar la imagen de cámara.
bg_path = args.bg
bg_base = cv2.imread(bg_path)
if bg_base is None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fallback_paths = [
        os.path.join(script_dir, 'assets', 'imagen_fondo.jpg'),
        os.path.join(script_dir, 'background.jpg'),
        os.path.join(script_dir, 'background.png'),
        os.path.join(script_dir, 'fondo.jpg'),
        os.path.join(script_dir, 'fondo.png'),
    ]
    for p in fallback_paths:
        bg_base = cv2.imread(p)
        if bg_base is not None:
            bg_path = p
            break

if bg_base is not None:
    game_bg = cv2.resize(bg_base, (width, height), interpolation=cv2.INTER_AREA)
    print(f'Fondo cargado: {bg_path}')
else:
    game_bg = np.zeros((height, width, 3), dtype=np.uint8)
    print('No se encontró imagen de fondo. Usando fondo negro.')

cv2.namedWindow("Image", cv2.WINDOW_NORMAL)
# Poner la ventana en fullscreen
cv2.setWindowProperty("Image", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
# Evitar franjas laterales por preservación de aspect ratio de la ventana.
cv2.setWindowProperty("Image", cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_FREERATIO)

puntaje = 0
pistola = Pistola(shot_cooldown=0.12)

# Control de FPS para optimizar rendimiento
target_fps = 30
frame_time = 1.0 / target_fps
last_frame_time = time.time()

while True:
    success, cam_img = dm.read()
    if not success or cam_img is None:
        continue

    # Solo usar cámara para tracking; no para render final.
    cam_img = cv2.flip(cam_img, 1)
    imgRGB = cv2.cvtColor(cam_img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    game_img = game_bg.copy()
    cam_h, cam_w = cam_img.shape[0:2]
    game_h, game_w = game_img.shape[0:2]

    shooting_now = False
    if results.multi_hand_landmarks:
        for handLms in results.multi_hand_landmarks:
            landmarks = {}
            for id, lm in enumerate(handLms.landmark):
                cx_cam, cy_cam = int(lm.x * cam_w), int(lm.y * cam_h)
                cx = int((cx_cam / max(1, cam_w)) * game_w)
                cy = int((cy_cam / max(1, cam_h)) * game_h)
                landmarks[id] = (cx, cy)

                if(id == 8):
                    # Se dibuja después de resolver el estado de disparo.
                    pass

            # Gesto de disparo: pulgar levantado.
            if 2 in landmarks and 3 in landmarks and 4 in landmarks and 8 in landmarks:
                x2, y2 = landmarks[2]  # thumb_mcp
                x3, y3 = landmarks[3]  # thumb_ip
                x4, y4 = landmarks[4]  # thumb_tip
                x8, y8 = landmarks[8]
                
                # Visualizar los puntos del pulgar en colores
                cv2.circle(game_img, (x2, y2), 8, (255, 0, 0), -1)  # Azul - thumb_mcp (base)
                cv2.circle(game_img, (x3, y3), 8, (0, 255, 0), -1)  # Verde - thumb_ip (medio)
                cv2.circle(game_img, (x4, y4), 8, (0, 0, 255), -1)  # Rojo - thumb_tip (punta)
                cv2.circle(game_img, (x8, y8), 8, (255, 255, 0), -1)  # Cyan - index_tip
                
                # Líneas para visualizar la dirección del pulgar
                cv2.line(game_img, (x2, y2), (x4, y4), (200, 200, 200), 2)
                
                # Actualizar estado de pistola basado en dirección del pulgar
                disparo_generado = pistola.actualizar_estado(landmarks)
                
                now = time.time()
                if disparo_generado:
                    shooting_now = True
                    pistola.reproducir_sonido()
                    puntaje = procesar_disparo(circulos, x4, y4, puntaje)

                # Dibujar arma en la posición del pulgar.
                pistola.dibujar(game_img, x4, y4, 2)
                
                # Obtener estado para la barra de carga
                energia = pistola.get_energia_carga()
                armada = pistola.esta_armada()
                
                # Barra de carga arriba de la pistola
                barra_y = y4 - 40
                barra_ancho = 40
                barra_alto = 6
                barra_x = x4 - barra_ancho // 2
                
                # Fondo de la barra
                cv2.rectangle(game_img, (barra_x, barra_y), (barra_x + barra_ancho, barra_y + barra_alto), (50, 50, 50), -1)
                
                # Barra de carga (color cambia según estado)
                if armada:
                    color_barra = (0, 255, 0)  # Verde cuando está armada
                else:
                    color_barra = (0, 165 + int(90 * energia), 255)  # Azul/Cyan progresivo
                
                carga_visual = int(barra_ancho * energia)
                cv2.rectangle(game_img, (barra_x, barra_y), (barra_x + carga_visual, barra_y + barra_alto), color_barra, -1)
                
                # Borde de la barra
                cv2.rectangle(game_img, (barra_x, barra_y), (barra_x + barra_ancho, barra_y + barra_alto), (200, 200, 200), 1)
                
                # Debug: mostrar estado actual
                estado_text = "ARMADA ✓" if armada else f"Cargando {int(energia*100)}%"
                debug_info = pistola.get_debug_info(landmarks)
                cv2.putText(game_img, estado_text, (10, 100), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 2)
                cv2.putText(game_img, debug_info, (10, 130), cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 200), 2)

    pintar_circulos(circulos, game_img)

    cv2.putText(game_img, str(int(puntaje)), (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)
    # Redimensionar por seguridad al tamaño del monitor.
    game_img = dm.resize_to_screen(game_img)

    cv2.imshow("Image", game_img)
    
    # Control de FPS: limitar a target_fps
    current_time = time.time()
    elapsed = current_time - last_frame_time
    if elapsed < frame_time:
        wait_ms = max(1, int((frame_time - elapsed) * 1000))
        k = cv2.waitKey(wait_ms)
    else:
        k = cv2.waitKey(1)
    
    last_frame_time = time.time()
    
    if k == 27:
        cv2.destroyAllWindows()
        dm.release()
        break
