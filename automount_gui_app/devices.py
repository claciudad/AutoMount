"""
Funciones auxiliares para obtener información de lsblk.
"""

from __future__ import annotations

import json
from typing import Dict, Iterable, Iterator, List

from .system import run_cmd

LSBLK_COLUMNS = "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT"


def load_block_devices() -> List[Dict]:
    """Devuelve la salida de lsblk parseada en JSON."""
    data = run_cmd(["lsblk", "-J", "-o", LSBLK_COLUMNS])
    parsed = json.loads(data)
    return parsed.get("blockdevices", [])


def flatten_lsblk(devices: Iterable[Dict]) -> Iterator[Dict]:
    """Itera productos de lsblk, incluyendo hijos."""
    for dev in devices:
        if dev.get("type") in {"disk", "part"}:
            yield dev
        for child in flatten_lsblk(dev.get("children") or []):
            yield child


def list_partition_entries() -> List[Dict]:
    """Retorna únicamente las entradas de tipo partición."""
    return [entry for entry in flatten_lsblk(load_block_devices()) if entry.get("type") == "part"]


__all__ = ["load_block_devices", "flatten_lsblk", "list_partition_entries"]
