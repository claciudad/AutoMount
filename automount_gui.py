#!/usr/bin/env python3
"""
Punto de entrada para la interfaz gráfica de AutoMount.
"""

import shutil
import sys
from pathlib import Path

import tkinter as tk

from automount_gui_app import AutoMountGUI, ensure_root


def main() -> None:
    ensure_root(Path(__file__).resolve())

    if not shutil.which("lsblk"):
        print("Error: se requiere lsblk para ejecutar esta aplicación.", file=sys.stderr)
        sys.exit(1)

    root = tk.Tk()
    AutoMountGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
