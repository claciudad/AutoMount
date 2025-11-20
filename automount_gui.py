#!/usr/bin/env python3
"""
Punto de entrada para la interfaz gráfica de AutoMount.
"""

import shutil
import sys
import os
from pathlib import Path

import tkinter as tk
from tkinter import messagebox

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


def request_admin(script_path: Path) -> bool:
    """
    Solicita elevación mediante un diálogo; si el usuario acepta,
    relanza con sudo y reemplaza el proceso actual.
    """
    if os.geteuid() == 0:
        return True

    temp_root = tk.Tk()
    temp_root.withdraw()
    answer = messagebox.askyesno(
        "Permisos requeridos",
        "Esta aplicación necesita privilegios de administrador para modificar /etc/fstab y montar unidades.\n\n"
        "¿Reiniciar con sudo ahora?",
        parent=temp_root,
    )
    temp_root.destroy()

    if answer:
        ensure_root(script_path)
        return False

    messagebox.showinfo(
        "Operación cancelada",
        "Se cerrará la aplicación porque no se otorgaron permisos de administrador.",
    )
    return False


def main() -> None:
    script_path = Path(__file__).resolve()
    if not request_admin(script_path):
        return

    if not shutil.which("lsblk"):
        print("Error: se requiere lsblk para ejecutar esta aplicación.", file=sys.stderr)
        sys.exit(1)

    root = create_root()
    AutoMountGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
