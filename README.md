# 🎮 Messi - Juego Interactivo con Reconocimiento de Manos

Juego FPS interactivo que utiliza reconocimiento de manos con MediaPipe. Controla una pistola futurista con tu mano, dispara a naves enemigas (rojas) y protege astronautas aliados (azules).

## 📋 Características

- 🎯 **Reconocimiento de manos**: Detección precisa de landmarks de MediaPipe
- 🔫 **Pistola futurista**: Perspectiva FPS con efectos visuales 3D
- 🚀 **Naves y astronautas**: Entidades animadas con comportamiento inteligente
- 💥 **Sistema de combate**: Dispara, carga y acumula puntos
- 🎨 **Efectos visuales**: Humo, explosiones y brillo futurista
- ⌨️ **Controles simples**: Gesto con pulgar para disparar

## 🏗️ Arquitectura

```
src/
├── core/                 # Componentes del sistema
│   ├── camera_manager.py # Gestión de cámara/pantalla
│   └── config.py        # Configuración centralizada
├── game/                # Lógica del juego
│   ├── space_entity.py  # Naves y astronautas
│   ├── weapon.py        # Sistema de arma
│   └── game_engine.py   # Motor del juego
└── ui/                  # Interfaz de usuario
    └── game_main.py     # Loop principal y entrada
```

### Principios de Diseño

✅ **Separación de Responsabilidades**: Cada módulo tiene una responsabilidad clara
✅ **Composición sobre Herencia**: Comportamiento mediante composición de objetos
✅ **KISS**: Soluciones simples y directas
✅ **Configuración Centralizada**: `config.py` con todas las constantes

## 🚀 Instalación

### Requisitos

- Python 3.8+
- pip

### Pasos

```bash
# 1. Clonar o descargar el proyecto
cd messi-project

# 2. Crear entorno e instalar dependencias
make setup

# 3. Ejecutar el juego
make start

# Alternativa: ejecutar como módulo
.venv/bin/python -m src

# Alternativa estilo comando de proyecto
pip install -e .
messi-start
```

## 🎮 Cómo Jugar

### Controles

| Acción | Tecla | Gesto |
|--------|-------|-------|
| Apuntar | Dedo índice | Mueve tu mano |
| Disparar | Pulgar arriba | Levanta el pulgar |
| Alternar fondo | `B` | - |
| Mostrar puntos mano | `H` | - |
| Salir | `ESC` | - |

### Objectivos

- 🎯 **Destruye naves rojas (malo)**: +2 puntos
- 🛡️ **Protege astronautas azules (bueno)**: -1 punto si los destruyes
- 🏆 **Maximiza tu puntuación**: Sé rápido y preciso

## ⚙️ Configuración Avanzada

Edita `src/core/config.py` para personalizar:

```python
# Número de entidades
NUM_ENTITIES = 10

# Tiempo de carga de la pistola (segundos)
WEAPON_CHARGE_TIME = 0.25

# Rango de detección de naves
ENTITY_ESCAPE_DETECTION_RANGE = 260

# Y más parámetros...
```

## 🔧 Argumentos de Línea de Comandos

```bash
# Usar cámara específica
python main.py --cam 1

# Usar imagen de fondo personalizada
python main.py --bg path/to/image.jpg

# Sin selector interactivo de cámara
make start-no-interactive

# Las mismas opciones también funcionan así
.venv/bin/python -m src --no-interactive
messi-start --no-interactive
```

## 📁 Estructura de Archivos

```
messi-project/
├── main.py                 # Punto de entrada
├── pyproject.toml          # Configuración del proyecto y script ejecutable
├── requirements.txt        # Dependencias
├── README.md              # Este archivo
├── .gitignore
├── assets/                # Recursos (imágenes, etc)
├── tests/                 # Tests automatizables
├── manual_tests/          # Pruebas manuales/visuales
└── src/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── camera_manager.py
    │   └── config.py
    ├── game/
    │   ├── __init__.py
    │   ├── space_entity.py
    │   ├── weapon.py
    │   └── game_engine.py
    └── ui/
        ├── __init__.py
        └── game_main.py
```

## 🔄 Flujo de la Aplicación

```
main.py
  └─ GameMain (ui/game_main.py)
      ├─ CameraManager (core/camera_manager.py)
      ├─ GameEngine (game/game_engine.py)
      │   ├─ Weapon (game/weapon.py)
      │   └─ SpaceEntity[] (game/space_entity.py)
      └─ MediaPipe Hands (detección de manos)
```

## 📊 Clases Principales

### `CameraManager`
Gestiona entrada de cámara o pantalla.

```python
manager = CameraManager(mode='camera')
success, frame = manager.read()
```

### `GameEngine`
Motor del juego con lógica de colisiones y física.

```python
engine = GameEngine(width, height)
engine.update(frame)
engine.process_shot(x, y)
```

### `Weapon`
Sistema de arma con carga y efectos.

```python
weapon = Weapon()
weapon.actualizar_estado(landmarks)
weapon.reproducir_sonido()
```

### `SpaceEntity`
Representa naves y astronautas.

```python
entity = SpaceEntity(x, y, size, tipo='malo')
entity.mover(width, height)
entity.dibujar(frame, escala=1.0)
```

## 🎨 Personalización Visual

### Colores y Estilos

Edita en `space_entity.py` y `weapon.py`:

```python
# Colores de naves
color_nave = (B, G, R)  # BGR format (OpenCV)
color_astronauta = (B, G, R)

# Efectos de brillo
glow_color = (120, 180, 255)
```

## 🐛 Solución de Problemas

| Problema | Solución |
|----------|----------|
| Cámara no se detecta | Verifica permisos de sistema, usa `--cam 0`, cierra otras apps |
| Bajo FPS | Reduce `NUM_ENTITIES`, baja resolución de pantalla |
| Mano no se detecta | Mejor iluminación, acércate a la cámara, mano visible |
| Importación fallida | Verifica que estés en el directorio correcto, usa `python main.py` |

## 📝 Licencia

Proyecto educativo de código abierto.

## 👨‍💻 Desarrollo

### Agregar Nueva Funcionalidad

1. Identifica el módulo correspondiente (core/game/ui)
2. Crea la clase/función en el módulo
3. Actualiza `config.py` si necesita constantes
4. Integra en `GameEngine` o `GameMain`

### Estándares de Código

- Python 3.8+
- Type hints apreciados
- Docstrings en módulos y clases
- Nombres descriptivos en español/inglés

## 🚀 Próximas Mejoras

- [ ] Guardar récrds de puntuación
- [ ] Diferentes dificultades
- [ ] Multijugador local
- [ ] Menú principal
- [ ] Efectos de sonido adicionales
- [ ] Power-ups

## 📞 Soporte

Para reportar problemas o sugerencias, abre un issue en el repositorio.

---

¡Diviértete jugando! 🎮✨
