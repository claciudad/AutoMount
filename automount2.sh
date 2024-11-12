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
if ! dpkg -s util-linux &> /dev/null; then
    echo "El script requiere util-linux (que contiene blkid) para funcionar correctamente."
    echo -e "\nDesea instalar util-linux ahora? (s: instalar / n: salir):"
    read -r respuesta
    if [[ "$respuesta" == "s" || "$respuesta" == "S" ]]; then
        echo -e "\nInstalando util-linux..."
        if apt-get update && apt-get install -y util-linux; then
            echo "util-linux se ha instalado correctamente."
        else
            echo "Error: No se pudo instalar util-linux. Verifique su conexión a Internet y los permisos."
            exit 1
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

# Verificar si la unidad ingresada es válida
if ! lsblk | grep -qw "$unidad"; then
    echo "Error: La unidad $unidad no existe. Por favor, verifique el nombre e intente nuevamente."
    exit 1
fi

# Preguntar el punto de montaje
echo -e "\nIngrese el punto de montaje (por ejemplo, /home/martinao/Disco1):"
read -r punto_montaje

# Crear el punto de montaje si no existe
if [ ! -d "$punto_montaje" ]; then
    echo "Creando el punto de montaje en $punto_montaje..."
    if ! mkdir -p "$punto_montaje"; then
        echo "Error: No se pudo crear el punto de montaje. Verifique los permisos y la ruta."
        exit 1
    fi
fi

# Asignar propiedad del punto de montaje al usuario
chown "$USER_ID":"$GROUP_ID" "$punto_montaje"

# Obtener UUID de la unidad seleccionada
uuid=$(blkid -s UUID -o value "/dev/$unidad")

# Obtener el tipo de sistema de archivos (FSTYPE) automáticamente
fstype=$(blkid -s TYPE -o value "/dev/$unidad")

# Verificar si se obtuvo el UUID y el tipo de sistema de archivos
if [ -n "$uuid" ] && [ -n "$fstype" ]; then
    # Verificar si ya existe una entrada en /etc/fstab
    if grep -q "UUID=$uuid" /etc/fstab; then
        echo "Error: Ya existe una entrada en /etc/fstab para esta unidad. No se realizarán cambios duplicados."
        exit 1
    fi

    # Definir opciones de montaje según el tipo de sistema de archivos
    case "$fstype" in
        ext4|ext3|ext2)
            # Para sistemas de archivos ext, la gestión de permisos se hace a nivel de sistema de archivos
            opciones="defaults,auto,user,rw,exec,umask=022"
            ;;
        ntfs|vfat|exfat)
            # Para NTFS, FAT32 y exFAT, asignar UID y GID al usuario
            opciones="defaults,auto,users,rw,exec,umask=022"
            ;;
        *)
            # Opciones predeterminadas para otros tipos de sistemas de archivos
            opciones="defaults,auto,users,rw,exec,umask=022"
            ;;
    esac

    # Confirmar con el usuario antes de modificar /etc/fstab
    echo -e "\nSe agregará la siguiente entrada a /etc/fstab:\nUUID=$uuid $punto_montaje $fstype $opciones 0 0"
    echo -e "\n¿Desea continuar con los cambios? (s/n):"
    read -r confirmacion
    if [[ "$confirmacion" != "s" && "$confirmacion" != "S" ]]; then
        echo "Operación cancelada por el usuario. Saliendo del script."
        exit 1
    fi

    # Agregar entrada en /etc/fstab con opciones determinadas
    echo "Agregando entrada a /etc/fstab..."
    if echo "UUID=$uuid $punto_montaje $fstype $opciones 0 0" >> /etc/fstab; then
        echo "La unidad se ha configurado para montarse automáticamente al iniciar."
    else
        echo "Error: No se pudo agregar la entrada a /etc/fstab. Verifique los permisos."
        exit 1
    fi

    # Montar la unidad inmediatamente para verificar
    echo "Montando la unidad..."
    if mount "$punto_montaje"; then
        echo "La unidad se ha montado correctamente en $punto_montaje. Para montarla manualmente en el futuro, use: mount $punto_montaje"
    else
        echo "Error: No se pudo montar la unidad. Verifique el sistema de archivos y los permisos."
        exit 1
    fi

    # Preguntar al usuario si desea ejecutar systemctl daemon-reload
    echo -e "\nPara aplicar los cambios en fstab, es recomendable ejecutar 'systemctl daemon-reload'."
    echo -e "¿Desea ejecutar este comando ahora? (s/n):"
    read -r reload_confirmacion
    if [[ "$reload_confirmacion" == "s" || "$reload_confirmacion" == "S" ]]; then
        if systemctl daemon-reload; then
            echo "systemctl daemon-reload se ejecutó correctamente."
        else
            echo "Error: No se pudo ejecutar 'systemctl daemon-reload'. Verifique los permisos."
        fi
    else
        echo "Recuerde ejecutar 'systemctl daemon-reload' en cuanto le sea posible para aplicar los cambios."
    fi

else
    echo "Error: No se encontró el UUID o el tipo de sistema de archivos de la unidad. Verifique que haya ingresado un nombre de unidad válido."
    exit 1
fi

# Texto simplificado en lugar de arte ASCII
echo
echo "------------------------------------------------"
echo "                 Speeder"
echo "------------------------------------------------"
echo "                by Quamagi & Bard"
echo

# Confirmación de finalización
echo "Configuración realizada correctamente."
