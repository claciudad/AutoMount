"""
Paquete de soporte para la aplicación AutoMount GUI.
"""

from .gui import AutoMountGUI
from .system import ensure_root

__all__ = ["AutoMountGUI", "ensure_root"]
