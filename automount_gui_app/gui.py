"""
Definición de la interfaz Tkinter para AutoMount.
"""

from __future__ import annotations

import tkinter as tk
import subprocess
import shutil
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict, Optional

try:
    from tkinter_tooltip import ToolTip  # type: ignore
except Exception:
    try:
        from tktooltip import ToolTip  # type: ignore
    except Exception:
        ToolTip = None  # type: ignore

try:
    from ttkbootstrap.icons import Icon  # type: ignore
except Exception:
    Icon = None

try:
    from tkterminal import Terminal  # type: ignore
except Exception:
    Terminal = None  # type: ignore

EMBEDDED_ICONS = {
    "arrow-repeat": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAiUlEQVR4nO1UWw6AIAwrxrNwSj85pZeZXyaL7FES1B/6ObqWDTZg4W8UllibyDN2HqXLr01Ex1MDSziDNtjeFAeAnRWP2hFdxKyAEbfiFi9sUSTOcsyyR8QzpBUsg+8N9MOygzY8B2yyPq9NxOJSLfJMmIE0//mMHXSjq2CmOOAsO2+xjQgv0LgAIgBNcyHMvIYAAAAASUVORK5CYII=",
    "folder": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAV0lEQVR4nGNgGAWjYBQwInPUWv7/p4aht2oY4eayoEtuT8Ot0XMWfnmYGmTARJrbSAc0CSIGBkQwYQTRonDKDY9biWDTPIhGLRi1gHKAkQ+Q0/AooAsAAGIODyaAXF99AAAAAElFTkSuQmCC",
    "check-circle": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAuklEQVR4nGNgGAUEACOxCk2OR/5HFztjuZygfoIKsBlMikU4JYgxmBiLsFqAzfDVut0Y6kIvlxK0hImQq1brdmM1HJel6ADDAmTXEzIAmw/QfU/QB5QCFAsocT2yemRziPIBtqAgFhC0AGY4siX4XI8OWIgxHBefkOEMDAR8QEwyJARQLEDOJDDX4rMEWQ7Zd8jmEBXJlPgEwwJsvkC2BJ1GV4deVNC8LBqY0pRUi8iqD4ixiJgabegDAO8tXkr1g8qcAAAAAElFTkSuQmCC",
    "box-arrow-down": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAcElEQVR4nGNgGAXDHjBiE3wdbPufXANF1x5GMZOJXIOIBSz4JNFdgw/g8jVeC/BpJNYhNA+ioW8BwTggJaJJtoCS/AADNA8ikryP7CNig45oH6AHF7HBR5QFuAwjxhKCFhAyhJD84IkDcgHNLRj6AAAKGScEtQuflAAAAABJRU5ErkJggg==",
    "clipboard": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAb0lEQVR4nGNgGAUDDRgJKYhKyvhPSM2yeTNwmsNEqotIBThtRnd5T0sdhpqSmiYUPjaf0NwHLMQqRHctsWDgfTCtr4OgIVlFFTjlBt4HDAz4XUjIh4PDB8TEA0UWjAYRQTCog4jo0pQYMCCl6dAHAOXiH/rvHeO8AAAAAElFTkSuQmCC",
}

from .devices import flatten_lsblk, load_block_devices
from .mounting import MountConfigurator, NTFSUnsupportedError
from .constants import FSTAB_PATH


if ToolTip is None:
    class SimpleToolTip:
        """Fallback de tooltip ligero si no hay dependencias externas."""

        def __init__(self, widget, text: str):
            self.widget = widget
            self.text = text
            self.tip_window = None
            widget.bind("<Enter>", self.show)
            widget.bind("<Leave>", self.hide)

        def show(self, _event=None):
            if self.tip_window or not self.text:
                return
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            self.tip_window = tk.Toplevel(self.widget)
            self.tip_window.wm_overrideredirect(True)
            self.tip_window.wm_geometry(f"+{x}+{y}")
            label = tk.Label(
                self.tip_window,
                text=self.text,
                justify=tk.LEFT,
                background="#2c2c2c",
                foreground="#ffffff",
                relief=tk.SOLID,
                borderwidth=1,
                padx=6,
                pady=3,
                font=("TkDefaultFont", 9),
            )
            label.pack(ipadx=1)

        def hide(self, _event=None):
            if self.tip_window:
                self.tip_window.destroy()
                self.tip_window = None

    ToolTip = SimpleToolTip  # type: ignore


APP_NAME = "AutoMount"
APP_VERSION = "1.0.0"
APP_CREDITS = "Martin Oviedo & Ashriel Lopez"


class AutoMountGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AutoMount GUI")
        self.root.geometry("720x600")

        self.unmounted_items: Dict[str, Dict] = {}
        self.mounted_items: Dict[str, Dict] = {}
        self._tooltips = []
        self._icon_cache: Dict[str, Optional[tk.PhotoImage]] = {}
        self._refreshing_devices = False
        if Icon is not None:
            try:
                self._icon_provider = Icon()
            except Exception:
                self._icon_provider = None
        else:
            self._icon_provider = None

        self.mount_configurator = MountConfigurator(self.log)

        self.style = ttk.Style(self.root)
        self._configure_styles()
        self._create_menus()
        self._build_widgets()
        self.refresh_devices()

    def _configure_styles(self) -> None:
        self.style.configure(
            "Dark.TButton",
            background="#3a3a3a",
            foreground="#ffffff",
            padding=6,
        )
        self.style.map(
            "Dark.TButton",
            background=[("active", "#4a4a4a")],
            foreground=[("disabled", "#a0a0a0")],
        )
        # Estilo tabla para Treeview
        self.style.configure(
            "Table.Treeview",
            background="#fafafa",
            fieldbackground="#fafafa",
            bordercolor="#c4c4c4",
            relief="flat",
            rowheight=24,
        )
        self.style.configure(
            "Table.Treeview.Heading",
            font=("TkDefaultFont", 10, "bold"),
            bordercolor="#c4c4c4",
            relief="raised",
        )
        self.style.map(
            "Table.Treeview",
            background=[("selected", "#d7e8ff")],
            foreground=[("selected", "#1d1d1d")],
        )

    def _create_menus(self) -> None:
        menubar = tk.Menu(self.root)
        menubar.add_command(label="Abrir fstab", command=self.open_fstab)
        menubar.add_command(label="Créditos", command=self.show_credits)
        self.root.config(menu=menubar)

        self.list_context_menu = tk.Menu(self.root, tearoff=0)
        self.list_context_menu.add_command(label="Copiar lista", command=self.copy_current_list)
        self._context_target = None

    def _build_widgets(self) -> None:
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        devices_frame = ttk.Frame(frame)
        devices_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        notebook = ttk.Notebook(devices_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "size", "type", "fstype", "mountpoint")

        unmounted_tab = ttk.Frame(notebook, padding=6)
        unmounted_container = ttk.Frame(unmounted_tab, borderwidth=1, relief="solid", padding=4)
        unmounted_container.grid(row=0, column=0, sticky="nsew")
        self.unmounted_tree = ttk.Treeview(
            unmounted_container, columns=columns, show="headings", selectmode="browse", height=14, style="Table.Treeview"
        )
        for col, text in zip(columns, ("Nombre", "Tamaño", "Tipo", "FS", "Punto de montaje")):
            self.unmounted_tree.heading(col, text=text)
            self.unmounted_tree.column(col, width=120 if col != "mountpoint" else 160, anchor="w")
        self.unmounted_tree.grid(row=0, column=0, sticky="nsew")
        unmounted_scroll = ttk.Scrollbar(unmounted_container, orient=tk.VERTICAL, command=self.unmounted_tree.yview)
        unmounted_scroll.grid(row=0, column=1, sticky="ns")
        self.unmounted_tree.configure(yscrollcommand=unmounted_scroll.set)
        self.unmounted_tree.bind("<Button-3>", lambda e: self.show_list_menu(e, self.unmounted_tree))
        self.unmounted_tree.tag_configure("odd", background="#f0f0f0")
        self.unmounted_tree.tag_configure("even", background="#fafafa")

        unmounted_container.columnconfigure(0, weight=1)
        unmounted_container.rowconfigure(0, weight=1)
        unmounted_tab.columnconfigure(0, weight=1)
        unmounted_tab.rowconfigure(0, weight=1)

        mounted_tab = ttk.Frame(notebook, padding=6)
        mounted_container = ttk.Frame(mounted_tab, borderwidth=1, relief="solid", padding=4)
        mounted_container.grid(row=0, column=0, sticky="nsew")
        self.mounted_tree = ttk.Treeview(
            mounted_container, columns=columns, show="headings", selectmode="browse", height=14, style="Table.Treeview"
        )
        for col, text in zip(columns, ("Nombre", "Tamaño", "Tipo", "FS", "Punto de montaje")):
            self.mounted_tree.heading(col, text=text)
            self.mounted_tree.column(col, width=120 if col != "mountpoint" else 160, anchor="w")
        self.mounted_tree.grid(row=0, column=0, sticky="nsew")
        mounted_scroll = ttk.Scrollbar(mounted_container, orient=tk.VERTICAL, command=self.mounted_tree.yview)
        mounted_scroll.grid(row=0, column=1, sticky="ns")
        self.mounted_tree.configure(yscrollcommand=mounted_scroll.set)
        self.mounted_tree.bind("<Button-3>", lambda e: self.show_list_menu(e, self.mounted_tree))
        self.mounted_tree.tag_configure("odd", background="#f0f0f0")
        self.mounted_tree.tag_configure("even", background="#fafafa")

        mounted_container.columnconfigure(0, weight=1)
        mounted_container.rowconfigure(0, weight=1)
        mounted_tab.columnconfigure(0, weight=1)
        mounted_tab.rowconfigure(0, weight=1)

        notebook.add(unmounted_tab, text="Unidades sin montar")
        notebook.add(mounted_tab, text="Unidades ya montadas")
        terminal_tab = ttk.Frame(notebook, padding=6)
        self._build_terminal_tab(terminal_tab)
        notebook.add(terminal_tab, text="Editar fstab (nano)")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(5, 15), sticky="w")
        refresh_icon = self.get_icon("arrow-repeat")
        refresh_btn = ttk.Button(
            btn_frame,
            text="Actualizar",
            command=self.refresh_devices,
            image=refresh_icon,
            compound=tk.LEFT if refresh_icon else tk.NONE,
            style="Dark.TButton",
        )
        refresh_btn.pack(side=tk.LEFT)
        self.add_tooltip(refresh_btn, "Vuelve a consultar lsblk para actualizar las tablas.")

        ttk.Label(frame, text="Punto de montaje").grid(row=2, column=0, sticky="w")
        mount_frame = ttk.Frame(frame)
        mount_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.mount_entry = ttk.Entry(mount_frame)
        self.mount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        select_icon = self.get_icon("folder")
        select_btn = ttk.Button(
            mount_frame,
            text="Seleccionar...",
            command=self.select_directory,
            image=select_icon,
            compound=tk.LEFT if select_icon else tk.NONE,
            style="Dark.TButton",
        )
        select_btn.pack(side=tk.LEFT, padx=(5, 0))
        self.add_tooltip(select_btn, "Abre un diálogo para elegir el directorio destino.")

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
        self.add_tooltip(
            self.umask_combo,
            "Permisos por defecto para sistemas no POSIX (NTFS, FAT, etc.).",
        )

        actions_frame = ttk.Frame(frame)
        actions_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        mount_icon = self.get_icon("check-circle")
        mount_btn = ttk.Button(
            actions_frame,
            text="Configurar montaje",
            command=self.configure_mount,
            image=mount_icon,
            compound=tk.LEFT if mount_icon else tk.NONE,
            style="Dark.TButton",
        )
        mount_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.add_tooltip(mount_btn, "Agrega la entrada en /etc/fstab y monta la unidad.")

        unmount_icon = self.get_icon("box-arrow-down")
        unmount_btn = ttk.Button(
            actions_frame,
            text="Desmontar",
            command=self.unmount_selected,
            image=unmount_icon,
            compound=tk.LEFT if unmount_icon else tk.NONE,
            style="Dark.TButton",
        )
        unmount_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        self.add_tooltip(unmount_btn, "Desmonta la unidad seleccionada y elimina su entrada.")

        log_header = ttk.Frame(frame)
        log_header.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(15, 0))
        ttk.Label(log_header, text="Registro").pack(side=tk.LEFT)
        copy_icon = self.get_icon("clipboard")
        copy_btn = ttk.Button(
            log_header,
            text="Copiar registro",
            command=self.copy_log,
            image=copy_icon,
            compound=tk.LEFT if copy_icon else tk.NONE,
            style="Dark.TButton",
        )
        copy_btn.pack(side=tk.RIGHT)
        self.add_tooltip(copy_btn, "Copia el historial de operaciones al portapapeles.")

        self.log_text = tk.Text(frame, height=8, state=tk.DISABLED)
        self.log_text.grid(row=7, column=0, columnspan=2, sticky="nsew")

        frame.rowconfigure(0, weight=3)
        frame.rowconfigure(7, weight=1)
        frame.columnconfigure(0, weight=1)

    def log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _run_in_thread(self, target, on_success=None, on_error=None) -> None:
        def worker():
            try:
                result = target()
                if on_success:
                    self.root.after(0, lambda: on_success(result))
            except Exception as exc:  # noqa: BLE001
                if on_error:
                    self.root.after(0, lambda: on_error(exc))
        threading.Thread(target=worker, daemon=True).start()

    def copy_log(self) -> None:
        content = self.log_text.get("1.0", tk.END).strip()
        if not content:
            self.log("No hay contenido para copiar.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.log("Registro copiado al portapapeles.")

    def refresh_devices(self) -> None:
        if self._refreshing_devices:
            return
        self._refreshing_devices = True
        self.log("Actualizando listas de unidades...")
        self._run_in_thread(
            target=self._load_devices_thread,
            on_success=self._populate_devices,
            on_error=self._populate_devices_error,
        )

    def _load_devices_thread(self):
        block_devices = load_block_devices()
        return flatten_lsblk(block_devices)

    def _populate_devices_error(self, exc: Exception) -> None:
        self._refreshing_devices = False
        self.log(f"Error al obtener las unidades: {exc}")
        messagebox.showerror("Error", f"No se pudieron obtener las unidades: {exc}")

    def _populate_devices(self, entries) -> None:
        for tree in (self.unmounted_tree, self.mounted_tree):
            for item in tree.get_children():
                tree.delete(item)
        self.unmounted_items.clear()
        self.mounted_items.clear()

        for idx, entry in enumerate(entries):
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
            tag = "even" if idx % 2 == 0 else "odd"
            if mountpoint:
                item_id = self.mounted_tree.insert("", tk.END, values=values, tags=(tag,))
                self.mounted_items[item_id] = entry
            else:
                item_id = self.unmounted_tree.insert("", tk.END, values=values, tags=(tag,))
                self.unmounted_items[item_id] = entry
        self._refreshing_devices = False

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

    def unmount_selected(self) -> None:
        try:
            selection = self._get_selected_mounted_device()
            if not selection:
                raise ValueError("Seleccione una unidad desde la tabla de montadas para desmontar.")

            success = self.mount_configurator.unmount(
                selection,
                confirm_action=self.confirm_unmount,
            )
            if success:
                messagebox.showinfo(
                    "Éxito", f"Se desmontó {selection['name']} y se eliminó su entrada de /etc/fstab."
                )
                self.refresh_devices()
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

    def _get_selected_mounted_device(self):
        selection = self.mounted_tree.selection()
        if selection:
            return self.mounted_items[selection[0]]
        return None

    def confirm_entry(self, entry: str) -> bool:
        return messagebox.askyesno(
            "Confirmar",
            f"Se agregará la siguiente entrada a /etc/fstab:\n{entry}\n\n¿Desea continuar?",
        )

    def confirm_unmount(self, device_name: str, mountpoint: str) -> bool:
        return messagebox.askyesno(
            "Confirmar desmontaje",
            f"Se desmontará {device_name} montado en {mountpoint} y se eliminará su entrada de /etc/fstab.\n"
            "¿Desea continuar?",
        )

    def open_fstab(self) -> None:
        path = FSTAB_PATH
        if not path.exists():
            messagebox.showerror("No encontrado", f"No se encontró {path}.")
            return
        opener = shutil.which("xdg-open")
        if opener:
            try:
                # Popen en vez de run para no bloquear si no hay entorno gráfico para root.
                subprocess.Popen([opener, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.log(f"Abrir {path} con xdg-open.")
                return
            except Exception as exc:
                self.log(f"Error al abrir {path}: {exc}")
                messagebox.showerror("Error", f"No se pudo abrir {path}.\n{exc}")
        self._show_fstab_viewer(path)

    def _show_fstab_viewer(self, path: Path) -> None:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo leer {path}.\n{exc}")
            return

        viewer = tk.Toplevel(self.root)
        viewer.title(f"Vista de {path}")
        viewer.geometry("720x480")
        viewer.transient(self.root)

        text_area = ScrolledText(viewer, wrap=tk.NONE)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_area.insert(tk.END, content)
        text_area.configure(state=tk.DISABLED)

        ttk.Button(viewer, text="Cerrar", command=viewer.destroy, style="Dark.TButton").pack(pady=(0, 10))

    def show_credits(self) -> None:
        credits_window = tk.Toplevel(self.root)
        credits_window.title("Créditos")
        credits_window.resizable(False, False)
        credits_window.transient(self.root)

        content = ttk.Frame(credits_window, padding=15)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(content, text=APP_NAME, font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
        ttk.Label(content, text=f"Versión: {APP_VERSION}").pack(anchor="w", pady=(4, 0))
        ttk.Label(content, text=f"Créditos: {APP_CREDITS}").pack(anchor="w", pady=(4, 10))

        close_btn = ttk.Button(content, text="Cerrar", command=credits_window.destroy, style="Dark.TButton")
        close_btn.pack(anchor="e")

    def _build_terminal_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        ttk.Label(
            tab,
            text="Edita /etc/fstab con nano dentro de la aplicación. Usa esta opción bajo tu propio riesgo.",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        if Terminal is None:
            missing = ttk.Label(
                tab,
                text="Falta dependencia opcional: instala tkterminal==0.4.0 para habilitar el terminal embebido.",
                foreground="#b22222",
                wraplength=520,
            )
            missing.grid(row=1, column=0, sticky="nsew")
            return

        container = ttk.Frame(tab, borderwidth=1, relief="solid")
        container.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.nano_terminal = Terminal(container, font=("TkFixedFont", 10))
        self.nano_terminal.grid(row=0, column=0, sticky="nsew")

        controls = ttk.Frame(tab)
        controls.grid(row=2, column=0, sticky="e")
        launch_btn = ttk.Button(
            controls,
            text="Abrir nano",
            command=self.launch_fstab_nano,
            style="Dark.TButton",
        )
        launch_btn.pack(side=tk.RIGHT)
        self.add_tooltip(launch_btn, "Inicia nano /etc/fstab en la terminal embebida.")

    def launch_fstab_nano(self) -> None:
        if Terminal is None or not hasattr(self, "nano_terminal"):
            messagebox.showerror(
                "Terminal no disponible",
                "Instala tkterminal==0.4.0 y reinicia la aplicación para usar nano embebido.",
            )
            return
        try:
            # Reinicia shell y abre nano sobre fstab
            self.nano_terminal.shell = True
            self.nano_terminal.clear()
            self.nano_terminal.run_command(f"nano {FSTAB_PATH}")
        except Exception as exc:
            self.log(f"No se pudo iniciar nano embebido: {exc}")
            messagebox.showerror("Error", f"No se pudo iniciar nano en el terminal embebido.\n{exc}")

    def get_icon(self, name: str) -> Optional[tk.PhotoImage]:
        if name in self._icon_cache:
            return self._icon_cache[name]

        icon_image: Optional[tk.PhotoImage] = None

        if hasattr(self, "_icon_provider") and self._icon_provider is not None:
            # ttkbootstrap provides a few baked-in base64 icons as attributes.
            icon_data = getattr(self._icon_provider, name, None)
            if isinstance(icon_data, str):
                try:
                    icon_image = tk.PhotoImage(data=icon_data)
                except Exception:
                    icon_image = None

        if icon_image is None:
            icon_data = EMBEDDED_ICONS.get(name)
            if icon_data:
                try:
                    icon_image = tk.PhotoImage(data=icon_data)
                except Exception:
                    icon_image = None

        self._icon_cache[name] = icon_image
        return icon_image

    def add_tooltip(self, widget, text: str) -> None:
        if ToolTip is None:
            return
        tooltip = None
        for kwargs in ({"text": text}, {"msg": text}):
            try:
                tooltip = ToolTip(widget, **kwargs)
                break
            except TypeError:
                continue
        if tooltip:
            self._tooltips.append(tooltip)


__all__ = ["AutoMountGUI"]
