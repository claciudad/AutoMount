"""
Definición de la interfaz Tkinter para AutoMount.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict

from .devices import flatten_lsblk, load_block_devices
from .mounting import MountConfigurator, NTFSUnsupportedError


class AutoMountGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AutoMount GUI")
        self.root.geometry("720x520")

        self.unmounted_items: Dict[str, Dict] = {}
        self.mounted_items: Dict[str, Dict] = {}

        self.mount_configurator = MountConfigurator(self.log)

        self._create_menus()
        self._build_widgets()
        self.refresh_devices()

    def _create_menus(self) -> None:
        self.list_context_menu = tk.Menu(self.root, tearoff=0)
        self.list_context_menu.add_command(label="Copiar lista", command=self.copy_current_list)
        self._context_target = None

    def _build_widgets(self) -> None:
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        devices_frame = ttk.Frame(frame)
        devices_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

        ttk.Label(devices_frame, text="Unidades sin montar").grid(row=0, column=0, sticky="w")
        ttk.Label(devices_frame, text="Unidades ya montadas").grid(row=0, column=2, sticky="w")

        columns = ("name", "size", "type", "fstype", "mountpoint")

        self.unmounted_tree = ttk.Treeview(
            devices_frame, columns=columns, show="headings", selectmode="browse", height=10
        )
        for col, text in zip(columns, ("Nombre", "Tamaño", "Tipo", "FS", "Punto de montaje")):
            self.unmounted_tree.heading(col, text=text)
            self.unmounted_tree.column(col, width=120 if col != "mountpoint" else 160, anchor="w")
        self.unmounted_tree.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        unmounted_scroll = ttk.Scrollbar(devices_frame, orient=tk.VERTICAL, command=self.unmounted_tree.yview)
        unmounted_scroll.grid(row=1, column=1, sticky="ns")
        self.unmounted_tree.configure(yscrollcommand=unmounted_scroll.set)
        self.unmounted_tree.bind("<Button-3>", lambda e: self.show_list_menu(e, self.unmounted_tree))

        self.mounted_tree = ttk.Treeview(
            devices_frame, columns=columns, show="headings", selectmode="browse", height=10
        )
        for col, text in zip(columns, ("Nombre", "Tamaño", "Tipo", "FS", "Punto de montaje")):
            self.mounted_tree.heading(col, text=text)
            self.mounted_tree.column(col, width=120 if col != "mountpoint" else 160, anchor="w")
        self.mounted_tree.grid(row=1, column=2, sticky="nsew", padx=(5, 0))
        mounted_scroll = ttk.Scrollbar(devices_frame, orient=tk.VERTICAL, command=self.mounted_tree.yview)
        mounted_scroll.grid(row=1, column=3, sticky="ns")
        self.mounted_tree.configure(yscrollcommand=mounted_scroll.set)
        self.mounted_tree.bind("<Button-3>", lambda e: self.show_list_menu(e, self.mounted_tree))

        devices_frame.columnconfigure(0, weight=1)
        devices_frame.columnconfigure(2, weight=1)
        devices_frame.rowconfigure(1, weight=1)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(5, 15), sticky="w")
        ttk.Button(btn_frame, text="Actualizar", command=self.refresh_devices).pack(side=tk.LEFT)

        ttk.Label(frame, text="Punto de montaje").grid(row=2, column=0, sticky="w")
        mount_frame = ttk.Frame(frame)
        mount_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.mount_entry = ttk.Entry(mount_frame)
        self.mount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(mount_frame, text="Seleccionar...", command=self.select_directory).pack(side=tk.LEFT, padx=(5, 0))

        options_frame = ttk.Frame(frame)
        options_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 15))
        ttk.Label(options_frame, text="Umask").pack(side=tk.LEFT)
        self.umask_var = tk.StringVar(value="000")
        self.umask_combo = ttk.Combobox(
            options_frame,
            textvariable=self.umask_var,
            values=("000", "002", "007", "022", "077"),
            state="readonly",
            width=5,
        )
        self.umask_combo.pack(side=tk.LEFT, padx=(5, 0))

        ttk.Button(frame, text="Configurar montaje", command=self.configure_mount).grid(
            row=5, column=0, columnspan=2, sticky="ew"
        )

        log_header = ttk.Frame(frame)
        log_header.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(15, 0))
        ttk.Label(log_header, text="Registro").pack(side=tk.LEFT)
        ttk.Button(log_header, text="Copiar registro", command=self.copy_log).pack(side=tk.RIGHT)

        self.log_text = tk.Text(frame, height=10, state=tk.DISABLED)
        self.log_text.grid(row=7, column=0, columnspan=2, sticky="nsew")

        frame.rowconfigure(0, weight=2)
        frame.rowconfigure(7, weight=1)
        frame.columnconfigure(0, weight=1)

    def log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def copy_log(self) -> None:
        content = self.log_text.get("1.0", tk.END).strip()
        if not content:
            self.log("No hay contenido para copiar.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.log("Registro copiado al portapapeles.")

    def refresh_devices(self) -> None:
        try:
            block_devices = load_block_devices()
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudieron obtener las unidades: {exc}")
            return

        for tree in (self.unmounted_tree, self.mounted_tree):
            for item in tree.get_children():
                tree.delete(item)
        self.unmounted_items.clear()
        self.mounted_items.clear()

        for entry in flatten_lsblk(block_devices):
            if entry.get("type") != "part":
                continue
            values = (
                entry.get("name", ""),
                entry.get("size", ""),
                entry.get("type", ""),
                entry.get("fstype", ""),
                entry.get("mountpoint", ""),
            )
            mountpoint = entry.get("mountpoint")
            if mountpoint:
                item_id = self.mounted_tree.insert("", tk.END, values=values)
                self.mounted_items[item_id] = entry
            else:
                item_id = self.unmounted_tree.insert("", tk.END, values=values)
                self.unmounted_items[item_id] = entry

    def show_list_menu(self, event, tree: ttk.Treeview) -> None:
        self._context_target = tree
        try:
            self.list_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.list_context_menu.grab_release()

    def copy_current_list(self) -> None:
        if not self._context_target:
            return
        entries = [
            "\t".join(self._context_target.item(item, "values")) for item in self._context_target.get_children()
        ]
        if not entries:
            self.log("No hay elementos para copiar.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(entries))
        self.log("Lista copiada al portapapeles.")

    def select_directory(self) -> None:
        directory = filedialog.askdirectory(title="Seleccione punto de montaje", mustexist=False)
        if directory:
            self.mount_entry.delete(0, tk.END)
            self.mount_entry.insert(0, directory)

    def configure_mount(self) -> None:
        try:
            selection = self._get_selected_device()
            if not selection:
                raise ValueError("Seleccione una unidad de alguna de las tablas.")
            mount_point = self.mount_entry.get().strip()
            if not mount_point:
                raise ValueError("Ingrese un punto de montaje.")

            umask_value = self.umask_var.get().strip() or "000"
            success = self.mount_configurator.configure(
                selection,
                mount_point,
                umask=umask_value,
                confirm_entry=self.confirm_entry,
            )
            if success:
                messagebox.showinfo("Éxito", f"Montaje configurado en {Path(mount_point)}.")
                self.refresh_devices()
        except NTFSUnsupportedError:
            messagebox.showerror(
                "NTFS no soportado",
                "El kernel no reconoce NTFS. Instala ntfs-3g e inténtalo nuevamente.\n"
                "La entrada en /etc/fstab fue restaurada."
            )
        except Exception as exc:
            self.log(f"Error: {exc}")
            messagebox.showerror("Error", str(exc))

    def _get_selected_device(self):
        selection = self.unmounted_tree.selection()
        if selection:
            return self.unmounted_items[selection[0]]
        selection = self.mounted_tree.selection()
        if selection:
            return self.mounted_items[selection[0]]
        return None

    def confirm_entry(self, entry: str) -> bool:
        return messagebox.askyesno(
            "Confirmar",
            f"Se agregará la siguiente entrada a /etc/fstab:\n{entry}\n\n¿Desea continuar?",
        )


__all__ = ["AutoMountGUI"]
