

# AutoMount - Montaje Automático de Unidades en Linux

Este script en bash permite listar las unidades de disco disponibles en el sistema, seleccionar una de ellas y configurarla para que se monte automáticamente al iniciar el sistema operativo. Ideal para usuarios de **Debian 12** y otras distribuciones basadas en Linux que necesiten un acceso rápido y sencillo a sus unidades en cada arranque.

## Descripción

**AutoMount** es un script diseñado para automatizar el proceso de montaje de unidades en Linux. Este script:

1. Lista las unidades de disco disponibles.
2. Permite al usuario seleccionar una unidad y un punto de montaje.
3. Configura el montaje automático en `/etc/fstab` para que la unidad se monte en cada reinicio del sistema.

Este proyecto fue realizado por **Daedalus** a solicitud de **Martín Oviedo**, quien identificó la necesidad de una herramienta de montaje accesible y directa para usuarios de Linux.

## Características Principales

- **Soporte para múltiples sistemas de archivos**: Incluye `ext4`, `ext3`, `ext2`, `ntfs`, `vfat`, `exfat`, `btrfs`, y `xfs`.
- **Interacción amigable**: Pregunta al usuario antes de realizar cambios críticos.
- **Validaciones robustas**: Verifica la existencia de la unidad, el punto de montaje y evita entradas duplicadas en `/etc/fstab`.
- **Compatibilidad amplia**: Funciona en distribuciones basadas en `apt`, `yum`, y `dnf`.

## Requisitos

- **Debian 12** o una distribución compatible (otras distribuciones pueden requerir adaptaciones).
- **util-linux** (que contiene el comando `blkid`).
- **Privilegios de superusuario** (`sudo`) para modificar el archivo `/etc/fstab`.
- **Bash**.

## Instalación

1. Clona este repositorio:

   ```bash
   git clone https://github.com/tuusuario/AutoMount.git
   cd AutoMount
   ```

2. Asegúrate de que el script tenga permisos de ejecución:

   ```bash
   chmod +x automount.sh
   ```

## Uso

### Script en Bash

1. Ejecuta el script con privilegios de superusuario:

   ```bash
   sudo ./automount.sh
   ```

2. El script mostrará una lista de las unidades disponibles.

3. Ingresa el nombre de la unidad que deseas montar (por ejemplo, `sda1`) y proporciona el punto de montaje deseado (por ejemplo, `/mnt/disco1`).

4. El script agregará automáticamente la configuración en `/etc/fstab` para que la unidad se monte en cada reinicio.

5. El script te preguntará si deseas ejecutar `systemctl daemon-reload` para aplicar los cambios inmediatamente. Si eliges no hacerlo, recuerda ejecutarlo cuando sea posible:

   ```bash
   sudo systemctl daemon-reload
   sudo mount -a
   ```

   Esto montará las unidades configuradas sin necesidad de reiniciar.

## Ejemplo de Uso

```bash
$ sudo ./automount.sh
Unidades disponibles:
sda                       931,5G disk 
└─sda1                    931,5G part 
sdb                       447,1G disk 
└─sdb1                    447,1G part 
nvme0n1                   894,3G disk 
├─nvme0n1p1                   1G part /boot/efi
├─nvme0n1p2                   2G part /boot
└─nvme0n1p3               891,2G part 

Ingrese el nombre de la unidad (por ejemplo, sda1) que desea montar automáticamente al iniciar:
sda1

Ingrese el punto de montaje (por ejemplo, /home/martin-oviedo/Disco1):
/home/martin-oviedo/Disco1

Se agregará la siguiente entrada a /etc/fstab:
UUID=69F35B7235F52F48 /home/martin-oviedo/Disco1 ntfs defaults,auto,users,rw,exec,uid=1000,gid=1000,umask=022 0 0
¿Desea continuar con los cambios? [S/N]: S
Agregando entrada a /etc/fstab...
La unidad se ha configurado para montarse automáticamente al iniciar.
Montando la unidad...
La unidad se ha montado correctamente en /home/martin-oviedo/Disco1.
¿Desea ejecutar 'systemctl daemon-reload' para aplicar los cambios en fstab? [S/N]: S
systemctl daemon-reload se ejecutó correctamente.
Configuración realizada correctamente.
```

### Interfaz gráfica en Python

También puedes utilizar la nueva interfaz Tkinter incluida en `automount_gui.py`. Requisitos adicionales:

- Python 3
- Tkinter (`sudo apt install python3-tk` en Debian/Ubuntu)

Ejecuta la aplicación con privilegios de superusuario:

```bash
sudo python3 automount_gui.py
```

La ventana mostrará las unidades disponibles, permitirá elegir el punto de montaje y se encargará de actualizar `/etc/fstab` creando un respaldo antes de aplicar los cambios.

## Créditos

Este script fue creado por **Daedalus** por solicitud de **Martín Oviedo**.

Si tienes preguntas o sugerencias, no dudes en contactarnos.

---

### Cambios Principales en el `README.md`:

1. **Nombre del Script**:
   - Actualicé el nombre del script de `montar_unidad.sh` a `automount.sh` para que sea más descriptivo.

2. **Características Principales**:
   - Añadí una sección para destacar las características principales del script, como el soporte para múltiples sistemas de archivos y las validaciones robustas.

3. **Ejemplo de Uso**:
   - Incluí un ejemplo detallado de cómo usar el script, basado en la salida que proporcionaste.

4. **Compatibilidad Amplia**:
   - Mencioné que el script es compatible con distribuciones basadas en `apt`, `yum`, y `dnf`.

5. **Limpieza y Claridad**:
   - Reorganicé el contenido para que sea más fácil de leer y seguir.

---
