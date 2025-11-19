#!/usr/bin/env python3
"""
Punto de entrada para la interfaz gráfica de AutoMount.
"""

import shutil
import sys
from pathlib import Path

import tkinter as tk

from automount_gui_app import AutoMountGUI, ensure_root

try:
    from ttkthemes import ThemedTk
except Exception:
    ThemedTk = None


def create_root() -> tk.Tk:
    if ThemedTk is not None:
        try:
            return ThemedTk(theme="equilux")
        except Exception:
            pass
    return tk.Tk()


def main() -> None:
    ensure_root(Path(__file__).resolve())

    if not shutil.which("lsblk"):
        print("Error: se requiere lsblk para ejecutar esta aplicación.", file=sys.stderr)
        sys.exit(1)

    root = create_root()
    AutoMountGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
