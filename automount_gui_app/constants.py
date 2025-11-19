"""
Constantes compartidas para AutoMount GUI.
"""

from pathlib import Path

FSTAB_PATH = Path("/etc/fstab")
PROTECTED_MOUNTPOINTS = {Path("/"), Path("/boot"), Path("/boot/efi")}

__all__ = ["FSTAB_PATH", "PROTECTED_MOUNTPOINTS"]
