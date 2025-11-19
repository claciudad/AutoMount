#!/usr/bin/env bash
# Genera un paquete .deb para la app GUI de AutoMount pidiendo datos básicos.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RELEASE_DIR="$ROOT_DIR/releases"

command -v dpkg-deb >/dev/null 2>&1 || {
  echo "dpkg-deb no está instalado. Instálalo (sudo apt-get install dpkg-dev) y reintenta." >&2
  exit 1
}

prompt() {
  local message="$1" default="$2" value
  read -r -p "$message [$default]: " value
  echo "${value:-$default}"
}

DEFAULT_VERSION="$(grep -Eo 'APP_VERSION\s*=\s*\"[^\"]+\"' "$ROOT_DIR/automount_gui_app/gui.py" | head -n1 | cut -d'\"' -f2)"
DEFAULT_VERSION="${DEFAULT_VERSION:-1.0.0}"

PKG_NAME="$(prompt 'Nombre del paquete' 'automount-gui')"
PKG_VERSION="$(prompt 'Versión del paquete' "$DEFAULT_VERSION")"
PKG_ARCH="$(prompt 'Arquitectura (all/amd64/arm64, etc.)' 'all')"
PKG_MAINTAINER="$(prompt 'Mantenedor (Nombre <email>)' 'Martin Oviedo <martin@example.com>')"
PKG_DESCRIPTION="$(prompt 'Descripción breve' 'Interfaz gráfica para AutoMount (montaje de unidades)')"

BUILD_DIR="$(mktemp -d)"
PKG_ROOT="$BUILD_DIR/${PKG_NAME}_${PKG_VERSION}"

cleanup() {
  rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

mkdir -p "$PKG_ROOT/DEBIAN"
mkdir -p "$PKG_ROOT/usr/local/share/$PKG_NAME"
mkdir -p "$PKG_ROOT/usr/local/bin"
mkdir -p "$RELEASE_DIR"

cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: $PKG_NAME
Version: $PKG_VERSION
Section: utils
Priority: optional
Architecture: $PKG_ARCH
Depends: python3 (>= 3.8), python3-tk, util-linux
Maintainer: $PKG_MAINTAINER
Description: $PKG_DESCRIPTION
EOF

cp "$ROOT_DIR/automount_gui.py" "$PKG_ROOT/usr/local/share/$PKG_NAME/"
cp -r "$ROOT_DIR/automount_gui_app" "$PKG_ROOT/usr/local/share/$PKG_NAME/"

cat > "$PKG_ROOT/usr/local/bin/$PKG_NAME" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
APP_DIR="/usr/local/share/REPLACE_PKG_NAME"
exec python3 "$APP_DIR/automount_gui.py" "$@"
EOF
sed -i "s/REPLACE_PKG_NAME/$PKG_NAME/g" "$PKG_ROOT/usr/local/bin/$PKG_NAME"
chmod 755 "$PKG_ROOT/usr/local/bin/$PKG_NAME"

OUTPUT_DEB="$RELEASE_DIR/${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}.deb"
dpkg-deb -b "$PKG_ROOT" "$OUTPUT_DEB" >/dev/null

echo "Paquete generado: $OUTPUT_DEB"
echo "Instala con: sudo dpkg -i \"$OUTPUT_DEB\""
