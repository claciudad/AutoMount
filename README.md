

# AutoMount - Montaje Automático de Unidades en Linux

Este script en bash permite listar las unidades de disco disponibles en el sistema, seleccionar una de ellas y configurarla para que se monte automáticamente al iniciar el sistema operativo. Ideal para usuarios de Debian 12 y otras distribuciones basadas en Linux que necesiten un acceso rápido y sencillo a sus unidades en cada arranque.

## Descripción

`AutoMount` es un script diseñado para automatizar el proceso de montaje de unidades en Linux. Este script lista las unidades disponibles y permite elegir cuál de ellas se montará automáticamente en el arranque. La configuración se guarda en el archivo `/etc/fstab`, permitiendo un montaje persistente a través de los reinicios del sistema.

Este proyecto fue realizado por **Daedalus** a solicitud de **Martín Oviedo**, quien identificó la necesidad de una herramienta de montaje accesible y directa para usuarios de Linux.

## Requisitos

- Debian 12 o una distribución compatible.
- Privilegios de superusuario (sudo) para modificar el archivo `/etc/fstab`.
- Bash.

## Instalación

1. Clona este repositorio:

   ```bash
   git clone https://github.com/tuusuario/AutoMount.git
   cd AutoMount
   ```

2. Asegúrate de que el script tenga permisos de ejecución:

   ```bash
   chmod +x montar_unidad.sh
   ```

## Uso

1. Ejecuta el script con privilegios de superusuario:

   ```bash
   sudo ./montar_unidad.sh
   ```

2. El script mostrará una lista de las unidades disponibles.

3. Ingresa el nombre de la unidad que deseas montar (por ejemplo, `sda1`) y proporciona el punto de montaje deseado (por ejemplo, `/mnt/disco1`).

4. El script agregará automáticamente la configuración en `/etc/fstab` para que la unidad se monte en cada reinicio.

5. Para verificar los cambios, puedes ejecutar:

   ```bash
   sudo systemctl daemon-reload
   sudo mount -a
   ```

   Esto montará las unidades configuradas sin necesidad de reiniciar.

## Créditos

Este script fue creado por **Daedalus** por solicitud de **Martín Oviedo**.  
Si tienes preguntas o sugerencias, no dudes en contactarnos.

---

Este README debería funcionar bien para tu repositorio en GitHub. Si necesitas modificar el nombre de usuario o la URL de GitHub, puedes personalizar esos detalles.
