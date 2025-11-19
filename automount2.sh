#!/bin/bash

# Función para solicitar confirmación al usuario
confirmacion() {
    while true; do
        read -rp "$1 [S/N]: " respuesta
        case "$respuesta" in
            [Ss]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Por favor, responda S o N.";;
        esac
    done
}

# Solicitar elevación de privilegios si no se ejecuta como root
if [[ "$EUID" -ne 0 ]]; then
    echo "Este script requiere permisos de administrador. Solicitando elevación..."
    exec sudo bash "$0" "$@"
fi

# Verificar si util-linux (que contiene blkid) está disponible e instalar si falta
if ! command -v blkid &> /dev/null; then
    echo "El script requiere util-linux (que contiene blkid) para funcionar correctamente."
    if confirmacion "¿Desea instalar util-linux ahora?"; then
        echo -e "\nInstalando util-linux..."
        if command -v apt-get &> /dev/null; then
            apt-get update && apt-get install -y util-linux
        elif command -v yum &> /dev/null; then
            yum install -y util-linux
        elif command -v dnf &> /dev/null; then
            dnf install -y util-linux
        else
            echo "Error: No se pudo identificar el gestor de paquetes. Instale util-linux manualmente."
            exit 1
        fi

        if ! command -v blkid &> /dev/null; then
            echo "Error: No se pudo instalar util-linux. Verifique su conexión a Internet y los permisos."
            exit 1
        else
            echo "util-linux se ha instalado correctamente."
        fi
    else
        echo "util-linux es necesario para continuar. Saliendo del script."
        exit 1
    fi
fi

# Obtener el usuario no root que ejecutó sudo
if [ "$SUDO_USER" ]; then
    USUARIO="$SUDO_USER"
else
    USUARIO=$(whoami)
fi

# Obtener UID y GID del usuario
USER_ID=$(id -u "$USUARIO")
GROUP_ID=$(id -g "$USUARIO")

# Listar las unidades disponibles
echo "Unidades disponibles:"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep 'disk\|part'

# Preguntar al usuario qué unidad desea montar automáticamente
echo -e "\nIngrese el nombre de la unidad (por ejemplo, sda1) que desea montar automáticamente al iniciar:"
read -r unidad

# Verificar si la unidad ingresada es válida usando listado simple de nombres
if ! lsblk -no NAME | grep -Fx -- "$unidad"; then
    echo "Error: La unidad $unidad no existe. Por favor, verifique el nombre e intente nuevamente."
    exit 1
fi

# Preguntar el punto de montaje
echo -e "\nIngrese el punto de montaje (por ejemplo, /home/$USUARIO/Disco1):"
read -r punto_montaje

# Verificar si el punto de montaje ya está en uso
if mountpoint -q "$punto_montaje"; then
    echo "Error: El punto de montaje $punto_montaje ya está en uso."
    exit 1
fi

# Crear el punto de montaje si no existe
if [ ! -d "$punto_montaje" ]; then
    echo "Creando el punto de montaje en $punto_montaje..."
    if ! mkdir -p "$punto_montaje"; then
        echo "Error: No se pudo crear el punto de montaje. Verifique los permisos y la ruta."
        exit 1
    fi
fi

# Obtener UUID de la unidad seleccionada
uuid=$(blkid -s UUID -o value "/dev/$unidad")

# Obtener el tipo de sistema de archivos (FSTYPE) automáticamente
fstype=$(blkid -s TYPE -o value "/dev/$unidad")

# Verificar si se obtuvo el UUID y el tipo de sistema de archivos
if [ -z "$uuid" ] || [ -z "$fstype" ]; then
    echo "Error: No se encontró el UUID o el tipo de sistema de archivos de la unidad. Verifique que haya ingresado un nombre de unidad válido."
    exit 1
fi

# Verificar si ya existe una entrada en /etc/fstab
if grep -q "UUID=$uuid" /etc/fstab; then
    echo "Error: Ya existe una entrada en /etc/fstab para esta unidad. No se realizarán cambios duplicados."
    exit 1
fi

# Definir opciones de montaje según el tipo de sistema de archivos
posix_fs=false
case "$fstype" in
    ext4|ext3|ext2)
        opciones="defaults,auto,user,rw,exec"
        posix_fs=true
        ;;
    ntfs|vfat|exfat)
        opciones="defaults,auto,users,rw,exec,uid=$USER_ID,gid=$GROUP_ID,umask=022"
        ;;
    btrfs|xfs)
        opciones="defaults,auto,users,rw,exec"
        posix_fs=true
        ;;
    *)
        opciones="defaults,auto,users,rw,exec,umask=022"
        ;;
esac

# Confirmar con el usuario antes de modificar /etc/fstab
entrada_fstab="UUID=$uuid $punto_montaje $fstype $opciones 0 0"
echo -e "\nSe agregará la siguiente entrada a /etc/fstab:\n$entrada_fstab"
if ! confirmacion "¿Desea continuar con los cambios?"; then
    echo "Operación cancelada por el usuario. Saliendo del script."
    exit 1
fi

# Crear respaldo de /etc/fstab antes de modificarlo
backup_fstab="/etc/fstab.backup-$(date +%Y%m%d%H%M%S)"
if cp /etc/fstab "$backup_fstab"; then
    echo "Respaldo creado en $backup_fstab."
else
    echo "Error: No se pudo crear el respaldo de /etc/fstab."
    exit 1
fi

# Agregar entrada en /etc/fstab con opciones determinadas
echo "Agregando entrada a /etc/fstab..."
if echo "$entrada_fstab" >> /etc/fstab; then
    echo "La unidad se ha configurado para montarse automáticamente al iniciar."
else
    echo "Error: No se pudo agregar la entrada a /etc/fstab. Verifique los permisos."
    echo "Restaurando /etc/fstab desde el respaldo..."
    cp "$backup_fstab" /etc/fstab
    exit 1
fi

# Montar la unidad inmediatamente para verificar
echo "Montando la unidad..."
if mount "$punto_montaje"; then
    if [ "$posix_fs" = true ]; then
        chown "$USER_ID":"$GROUP_ID" "$punto_montaje"
    fi
    echo "La unidad se ha montado correctamente en $punto_montaje. Para montarla manualmente en el futuro, use: mount $punto_montaje"
else
    echo "Error: No se pudo montar la unidad. Verifique el sistema de archivos y los permisos."
    echo "Restaurando /etc/fstab desde el respaldo..."
    if cp "$backup_fstab" /etc/fstab; then
        echo "Se restauró /etc/fstab a su estado anterior."
    else
        echo "Advertencia: No se pudo restaurar automáticamente /etc/fstab. Revíselo manualmente utilizando $backup_fstab."
    fi
    exit 1
fi

# Preguntar al usuario si desea ejecutar systemctl daemon-reload
if confirmacion "¿Desea ejecutar 'systemctl daemon-reload' para aplicar los cambios en fstab?"; then
    if systemctl daemon-reload; then
        echo "systemctl daemon-reload se ejecutó correctamente."
    else
        echo "Error: No se pudo ejecutar 'systemctl daemon-reload'. Verifique los permisos."
    fi
else
    echo "Recuerde ejecutar 'systemctl daemon-reload' en cuanto le sea posible para aplicar los cambios."
fi

# Confirmación de finalización
echo "Configuración realizada correctamente."
