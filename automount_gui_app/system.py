"""
Funciones relacionadas con interacción del sistema y privilegios.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence


def run_cmd(cmd: Sequence[str], check: bool = True, capture_output: bool = True) -> str:
    """
    Ejecuta un comando y devuelve stdout. Lanza RuntimeError si falla y check es True.
    """
    result = subprocess.run(cmd, text=True, capture_output=capture_output)
    if check and result.returncode != 0:
        error_msg = result.stderr.strip() if capture_output else ""
        raise RuntimeError(error_msg or f"Error ejecutando {' '.join(cmd)}")
    return result.stdout.strip() if capture_output else ""


def is_mountpoint(path: Path) -> bool:
    """Indica si la ruta ya es un punto de montaje activo."""
    result = subprocess.run(["mountpoint", "-q", str(path)])
    return result.returncode == 0


def ensure_root(target_script: Path | None = None) -> None:
    """Solicita privilegios de administrador en caso de no ejecutarse como root."""
    if os.geteuid() == 0:
        return

    if shutil.which("sudo"):
        script_path = target_script or Path(__file__).resolve()
        cmd = ["sudo", sys.executable, str(script_path), *sys.argv[1:]]
        print("Solicitando privilegios de administrador...", file=sys.stderr)
        os.execvp("sudo", cmd)

    print("Error: esta aplicación debe ejecutarse con privilegios de administrador (sudo).", file=sys.stderr)
    sys.exit(1)


__all__ = ["run_cmd", "is_mountpoint", "ensure_root"]
