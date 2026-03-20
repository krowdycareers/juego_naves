"""Backends de renderizado del juego."""

from .opencv_entity_renderer import OpenCVEntityRenderer
from .opencv_weapon_renderer import OpenCVWeaponRenderer

__all__ = ["OpenCVEntityRenderer", "OpenCVWeaponRenderer"]
