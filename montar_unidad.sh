#!/bin/bash

# Listar las unidades disponibles
echo "Unidades disponibles:"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep 'disk\|part'

# Preguntar al usuario qué unidad desea montar automáticamente
echo -e "\nIngrese el nombre de la unidad (por ejemplo, sda1) que desea montar automáticamente al iniciar:"
read unidad

# Preguntar el punto de montaje
echo -e "\nIngrese el punto de montaje (por ejemplo, /mnt/mi_unidad):"
read punto_montaje

# Crear el punto de montaje si no existe
if [ ! -d "$punto_montaje" ]; then
  sudo mkdir -p "$punto_montaje"
fi

# Obtener UUID de la unidad seleccionada
uuid=$(blkid -s UUID -o value /dev/"$unidad")

# Agregar entrada en /etc/fstab para el montaje automático
if [ -n "$uuid" ]; then
  echo "UUID=$uuid $punto_montaje auto defaults 0 0" | sudo tee -a /etc/fstab
  echo "La unidad se ha configurado para montarse automáticamente en el arranque."
else
  echo "No se encontró el UUID de la unidad. Verifique que haya ingresado un nombre de unidad válido."
fi
