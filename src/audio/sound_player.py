"""Implementaciones de salida de audio del juego."""

from __future__ import annotations

import platform
import subprocess
import threading
from typing import Protocol


class SoundPlayer(Protocol):
    """Puerto simple para reproducir sonidos del juego."""

    def play_shot(self) -> None:
        """Reproduce el sonido de disparo."""

    def play_target_hit(self, entity_type: str) -> None:
        """Reproduce el sonido asociado al objetivo destruido."""


class SystemSoundPlayer:
    """Reproductor de sonidos basado en capacidades nativas del sistema."""

    def play_shot(self) -> None:
        self._play_async(self._play_shot_sound)

    def play_target_hit(self, entity_type: str) -> None:
        self._play_async(lambda: self._play_target_sound(entity_type))

    def _play_async(self, callback) -> None:
        threading.Thread(target=callback, daemon=True).start()

    def _play_shot_sound(self) -> None:
        try:
            system = platform.system().lower()
            if system == "darwin":
                subprocess.Popen(
                    ["afplay", "/System/Library/Sounds/Pop.aiff"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif system.startswith("win"):
                import winsound

                winsound.PlaySound(
                    "SystemAsterisk",
                    winsound.SND_ALIAS | winsound.SND_ASYNC,
                )
            else:
                print("\a", end="", flush=True)
        except Exception:
            pass

    def _play_target_sound(self, entity_type: str) -> None:
        try:
            system = platform.system().lower()

            if str(entity_type).lower() == "malo":
                mac_sound = "/System/Library/Sounds/Glass.aiff"
                win_alias = "SystemHand"
            else:
                mac_sound = "/System/Library/Sounds/Funk.aiff"
                win_alias = "SystemExclamation"

            if system == "darwin":
                subprocess.Popen(
                    ["afplay", mac_sound],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif system.startswith("win"):
                import winsound

                winsound.PlaySound(
                    win_alias,
                    winsound.SND_ALIAS | winsound.SND_ASYNC,
                )
            else:
                print("\a", end="", flush=True)
        except Exception:
            pass
