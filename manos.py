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

def pintar_circulos(circulos, img, puntaje, apuntador=None):
    HEIGHT, WIDTH = img.shape[0:2]

    for c in circulos:
        reaparecio = c.actualizar_explosion_y_reaparicion()
        if reaparecio:
            c.x = random.randint(0, max(0, WIDTH - c.size))
            c.y = random.randint(0, max(0, HEIGHT - c.size))

    for i in range(len(circulos)):
            for j in range(i + 1, len(circulos)):
                a = circulos[i]
                b = circulos[j]
                if (not a.activo) or (not b.activo) or a.en_explosion or b.en_explosion:
                    continue

                misma_altura = abs(a.y - b.y) <= max(8, int(min(a.size, b.size) * 0.75))
                opuestos = a.tipo != b.tipo

                # Si colisionan y están en la "misma altura" (mismo plano), explotan ambos.
                if opuestos and misma_altura and a.detectar_colision(b):
                    a.iniciar_explosion(frames_explosion=10, iteraciones_reaparicion=random.randint(1, 10))
                    b.iniciar_explosion(frames_explosion=10, iteraciones_reaparicion=random.randint(1, 10))
                    puntaje -= 1
                    continue

                a.rebotar(b)
                    
    for circulo in circulos:
        if not circulo.activo:
            continue

        # Hacer que los malos "huyan" del apuntador (dedo índice)
        if apuntador is not None and circulo.tipo == 'malo' and not circulo.en_explosion:
            ax, ay = apuntador
            dx = circulo.x - ax
            dy = circulo.y - ay
            dist = math.hypot(dx, dy)

            # Solo reaccionar si el jugador está relativamente cerca
            if dist < 260:
                # Dirección normalizada alejándose del apuntador
                if dist > 1e-3:
                    ndx = dx / dist
                    ndy = dy / dist
                else:
                    ndx, ndy = 0.0, 0.0

                # Velocidad objetivo más alta cuando está muy cerca
                base_speed = max(6.0, min(14.0, 14.0 * (1.0 - dist / 260.0)))
                target_vx = ndx * base_speed
                target_vy = ndy * base_speed

                # Suavizar cambio de velocidad para que no sea brusco
                mezcla = 0.35
                circulo.vx = (1.0 - mezcla) * circulo.vx + mezcla * target_vx
                circulo.vy = (1.0 - mezcla) * circulo.vy + mezcla * target_vy

        circulo.mover(WIDTH, HEIGHT)
        escala_base = 0.85 if circulo.tipo == 'malo' else 0.9
        escala = escala_base * circulo.escala_por_altura(HEIGHT)
        circulo.dibujar(img, escala=escala)

    return img, puntaje


def procesar_disparo(circulos, x_mira, y_mira, puntaje, pistola):
    radio_objetivo = 30
    for c in circulos:
        if not c.activo or c.en_explosion:
            continue
        if math.hypot(c.x - x_mira, c.y - y_mira) <= radio_objetivo:
            pistola.reproducir_sonido_objetivo(c.tipo)
            if c.tipo == 'malo':
                puntaje += 2
            else:
                puntaje -= 1
            c.iniciar_explosion(frames_explosion=10, iteraciones_reaparicion=random.randint(1, 10))
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
                      max_num_hands=1,
                      min_detection_confidence=0.5,
                      min_tracking_confidence=0.5)
mpDraw = mp.solutions.drawing_utils

circulos = generar_circulos(10, width, height, 20)

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

# Variables para guardar estado de la pistola entre frames
pistola_x = 0
pistola_y = 0
show_pistola = False

# Control de FPS para optimizar rendimiento
target_fps = 30
frame_time = 1.0 / target_fps
last_frame_time = time.time()
mostrar_fondo = True
mostrar_puntos_mano = False

while True:
    success, cam_img = dm.read()
    if not success or cam_img is None:
        continue

    # Solo usar cámara para tracking; no para render final directo (salvo cuando se pide con 'b').
    cam_img = cv2.flip(cam_img, 1)
    imgRGB = cv2.cvtColor(cam_img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)
    print(results.multi_hand_landmarks)
    
    if mostrar_fondo:
        game_img = game_bg.copy()
    else:
        # Usar lo que ve la cámara como fondo de juego
        game_img = cv2.resize(
            cam_img,
            (game_bg.shape[1], game_bg.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
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
                
                # Visualizar los puntos y la dirección solo si está habilitado
                if mostrar_puntos_mano:
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
                    # Usar el dedo índice como apuntador
                    puntaje = procesar_disparo(circulos, x8, y8, puntaje, pistola)

                # Guardar coordenadas para dibujar después (apuntador = dedo índice)
                pistola_x = x8
                pistola_y = y8
                show_pistola = True
                
                # Debug: mostrar estado actual
                energia = pistola.get_energia_carga()
                armada = pistola.esta_armada()
                estado_text = "ARMADA ✓" if armada else f"Cargando {int(energia*100)}%"
                #debug_info = pistola.get_debug_info(landmarks)
                cv2.putText(game_img, estado_text, (10, 100), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255), 2)
                #cv2.putText(game_img, debug_info, (10, 130), cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 200), 2)

    # Dibujar los objetos móviles (naves y ovnis)
    apuntador = (pistola_x, pistola_y) if show_pistola else None
    game_img, puntaje = pintar_circulos(circulos, game_img, puntaje, apuntador)
    
    # Dibujar pistola DESPUÉS de los objetos móviles
    if show_pistola:
        pistola.dibujar(game_img, pistola_x, pistola_y, 2)
        
        # Obtener estado para la barra de carga
        energia = pistola.get_energia_carga()
        armada = pistola.esta_armada()
        
        # Barra de carga arriba de la pistola
        barra_y = pistola_y - 40
        barra_ancho = 40
        barra_alto = 6
        barra_x = pistola_x - barra_ancho // 2
        
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
        
        # Reset para el siguiente frame
        show_pistola = False

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
    
    if k == ord('b') or k == ord('B'):
        mostrar_fondo = not mostrar_fondo
    if k == ord('h') or k == ord('H'):
        mostrar_puntos_mano = not mostrar_puntos_mano
    if k == 27:
        cv2.destroyAllWindows()
        dm.release()
        break
