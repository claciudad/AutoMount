"""
Lógica para validar y configurar montajes persistentes.
"""

from __future__ import annotations

import datetime
import os
import pwd
import shutil
from pathlib import Path
from typing import Callable, Dict, Tuple

from .constants import FSTAB_PATH, PROTECTED_MOUNTPOINTS
from .system import is_mountpoint, run_cmd

PROTECTED_PATHS = {path.as_posix() for path in PROTECTED_MOUNTPOINTS}

class NTFSUnsupportedError(RuntimeError):
    """Error especializado cuando falta soporte NTFS en el sistema."""


class MountConfigurator:
    """Encapsula la lógica necesaria para registrar montajes en /etc/fstab."""

    def __init__(self, log_callback: Callable[[str], None]) -> None:
        self.log = log_callback

    def configure(
        self,
        device_info: Dict,
        mount_point: str,
        umask: str,
        confirm_entry: Callable[[str], bool],
    ) -> bool:
        device_name = device_info["name"]
        self._ensure_device_available(device_name)

        mount_path = Path(mount_point)
        self.log(f"Punto de montaje seleccionado: {mount_path}")
        self._prepare_mount_directory(mount_path)
        umask_value = self._sanitize_umask(umask)

        user_info = self._resolve_user_info()
        uuid, fstype = self._obtain_device_identifiers(device_name, device_info)
        self._ensure_fstab_entry_absent(uuid)

        options, posix_fs = mount_options(fstype, user_info.pw_uid, user_info.pw_gid, umask_value)
        entry = f"UUID={uuid} {mount_path} {fstype} {options} 0 0"

        if not confirm_entry(entry):
            self.log("Operación cancelada por el usuario.")
            return False

        backup_path = create_fstab_backup()
        self.log(f"Respaldo de /etc/fstab creado en {backup_path}")

        try:
            with FSTAB_PATH.open("a", encoding="utf-8") as fstab_file:
                fstab_file.write(f"{entry}\n")
            self.log("Entrada añadida correctamente.")

            self.log("Montando unidad para validar...")
            run_cmd(["mount", str(mount_path)])
            if posix_fs:
                os.chown(mount_path, user_info.pw_uid, user_info.pw_gid)

            self.log(f"La unidad se montó correctamente en {mount_path}.")
            return True
        except RuntimeError as exc:
            self._handle_mount_error(exc, backup_path)
        except Exception:
            self.log("Ocurrió un error. Restaurando /etc/fstab desde el respaldo.")
            shutil.copy(backup_path, FSTAB_PATH)
            raise
        return False

    def unmount(
        self,
        device_info: Dict,
        confirm_action: Callable[[str, str], bool],
    ) -> bool:
        mountpoint = device_info.get("mountpoint")
        if not mountpoint or not mountpoint.startswith("/"):
            raise ValueError("La unidad seleccionada no tiene un punto de montaje válido para desmontar.")
        mount_path = Path(mountpoint)
        if is_protected_mountpoint(mount_path):
            raise ValueError("No se puede desmontar este punto de montaje desde la aplicación.")

        device_name = device_info["name"]
        uuid, _ = self._obtain_device_identifiers(device_name, device_info)

        if not confirm_action(device_name, mountpoint):
            self.log("Operación cancelada por el usuario.")
            return False

        backup_path = create_fstab_backup()
        self.log(f"Respaldo de /etc/fstab creado en {backup_path}")

        try:
            self.log(f"Desmontando {device_name} de {mountpoint}...")
            run_cmd(["umount", mountpoint])
            self.log("Unidad desmontada correctamente.")
            remove_fstab_entry(uuid, mountpoint)
            self.log("La entrada correspondiente se eliminó de /etc/fstab.")
            return True
        except Exception:
            self.log("Ocurrió un error. Restaurando /etc/fstab desde el respaldo.")
            shutil.copy(backup_path, FSTAB_PATH)
            raise

    def _prepare_mount_directory(self, mount_path: Path) -> None:
        if is_mountpoint(mount_path):
            raise ValueError(f"El punto de montaje {mount_path} ya está en uso.")

        if not mount_path.exists():
            self.log(f"Creando directorio {mount_path}")
            mount_path.mkdir(parents=True, exist_ok=True)

    def _resolve_user_info(self):
        user_name = os.environ.get("SUDO_USER") or pwd.getpwuid(os.geteuid()).pw_name
        return pwd.getpwnam(user_name)

    def _obtain_device_identifiers(self, device_name: str, device_info: Dict) -> Tuple[str, str]:
        uuid = run_cmd(["blkid", "-s", "UUID", "-o", "value", f"/dev/{device_name}"])
        fstype = run_cmd(["blkid", "-s", "TYPE", "-o", "value", f"/dev/{device_name}"])
        if uuid and fstype:
            return uuid, fstype
        hint = ""
        if device_info.get("type") == "disk":
            hint = (
                "\nConsejo: Seleccione una partición (tipo 'part') en lugar del disco completo "
                "o cree una partición/formatee la unidad."
            )
        raise RuntimeError(f"No se pudo determinar UUID o tipo de sistema de archivos para /dev/{device_name}.{hint}")

    def _ensure_fstab_entry_absent(self, uuid: str) -> None:
        with FSTAB_PATH.open("r", encoding="utf-8") as fstab_file:
            if f"UUID={uuid}" in fstab_file.read():
                raise RuntimeError("Ya existe una entrada en /etc/fstab para esta unidad.")

    def _ensure_device_available(self, device_name: str) -> None:
        available_names = [
            name.lstrip("├─└─│ ")
            for name in run_cmd(["lsblk", "-ln", "-o", "NAME"]).splitlines()
        ]
        if device_name not in available_names:
            raise ValueError(f"La unidad {device_name} ya no está disponible.")

    def _sanitize_umask(self, umask: str) -> str:
        umask = (umask or "000").strip()
        if len(umask) == 3 and all(ch in "01234567" for ch in umask):
            return umask
        self.log(f"Umask inválido '{umask}', usando 000 como valor por defecto.")
        return "000"

    def _handle_mount_error(self, exc: RuntimeError, backup_path: Path) -> None:
        message = str(exc)
        self.log("Ocurrió un error. Restaurando /etc/fstab desde el respaldo.")
        shutil.copy(backup_path, FSTAB_PATH)
        if "unknown filesystem type 'ntfs'" in message.lower():
            self.log(
                "El sistema informa 'unknown filesystem type NTFS'. "
                "Instala ntfs-3g (sudo apt-get install ntfs-3g) para habilitar soporte NTFS con escritura."
            )
            raise NTFSUnsupportedError(message) from exc
        raise


def mount_options(fstype: str, uid: int, gid: int, umask: str) -> Tuple[str, bool]:
    posix_fs = False
    if fstype in {"ext4", "ext3", "ext2"}:
        opts = "defaults,auto,user,rw,exec"
        posix_fs = True
    elif fstype in {"ntfs", "vfat", "exfat"}:
        opts = f"defaults,auto,users,rw,exec,uid={uid},gid={gid},umask={umask}"
    elif fstype in {"btrfs", "xfs"}:
        opts = "defaults,auto,users,rw,exec"
        posix_fs = True
    else:
        opts = f"defaults,auto,users,rw,exec,uid={uid},gid={gid},umask={umask}"
    return opts, posix_fs


def create_fstab_backup() -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = FSTAB_PATH.with_name(f"fstab.backup-{timestamp}")
    shutil.copy(FSTAB_PATH, backup_path)
    return backup_path


def remove_fstab_entry(uuid: str, mountpoint: str) -> None:
    removed = False
    with FSTAB_PATH.open("r", encoding="utf-8") as fstab_file:
        lines = fstab_file.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        parts = stripped.split()
        if len(parts) >= 2 and parts[0] == f"UUID={uuid}" and parts[1] == mountpoint:
            removed = True
            continue
        new_lines.append(line)

    if not removed:
        raise RuntimeError("No se encontró una entrada en /etc/fstab para esta unidad.")

    with FSTAB_PATH.open("w", encoding="utf-8") as fstab_file:
        fstab_file.writelines(new_lines)


def is_protected_mountpoint(path: Path) -> bool:
    return path.as_posix() in PROTECTED_PATHS


__all__ = [
    "MountConfigurator",
    "NTFSUnsupportedError",
    "mount_options",
    "create_fstab_backup",
    "remove_fstab_entry",
]
