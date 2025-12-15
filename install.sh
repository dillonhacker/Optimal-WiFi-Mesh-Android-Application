#!/usr/bin/env bash
set -euo pipefail

# ---- Helpers ----
log() { echo -e "\n[*] $*\n"; }
die() { echo -e "\n[!] $*\n" >&2; exit 1; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

log "Project root: $PROJECT_ROOT"

# ---- 0) Basic checks ----
command -v sudo >/dev/null 2>&1 || die "sudo not found. Install sudo or run as root."
command -v apt >/dev/null 2>&1 || die "apt not found. This script is for Ubuntu/Debian."

# ---- 1) System packages (fresh Ubuntu 24.04) ----
log "Installing system dependencies (build tools, Python venv, libs)..."
sudo apt update
sudo apt install -y --no-install-recommends \
  ca-certificates curl git unzip \
  build-essential pkg-config \
  python3 python3-pip python3-venv \
  libssl-dev libffi-dev \
  protobuf-compiler libprotobuf-dev \
  automake autoconf libtool \
  clang \
  cmake

# Notes:
# - build-essential/pkg-config/clang/cmake: common for Rust/PyO3 native builds
# - libssl-dev/libffi-dev: common wheels/native deps
# - protobuf-compiler/libprotobuf-dev: needed for sdhash blooms.proto step

# ---- 2) Rust toolchain (fresh system) ----
if ! command -v cargo >/dev/null 2>&1; then
  log "Installing Rust toolchain via rustup (stable)..."
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  # load rustup environment for this script
  source "$HOME/.cargo/env"
else
  log "Rust (cargo) already present."
fi

# Ensure rust is on PATH even in non-login shells
if ! grep -q 'source "$HOME/.cargo/env"' "$HOME/.bashrc" 2>/dev/null; then
  echo 'source "$HOME/.cargo/env"' >> "$HOME/.bashrc"
fi

# ---- 3) Python venv ----
log "Creating Python virtual environment (./venv)..."
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# Activate for this script
source venv/bin/activate

log "Upgrading pip tooling in venv..."
python -m pip install --upgrade pip wheel setuptools

# ---- 4) Install Python requirements ----
if [ -f "requirements.txt" ]; then
  log "Installing Python dependencies from requirements.txt..."
  python -m pip install -r requirements.txt
else
  log "requirements.txt not found; skipping."
fi

# ---- 5) Build/install your PyO3 module (wifi_backend) ----
# Assumption: Rust crate for the PyO3 module is in ./backend (common).
# If it's elsewhere, update BACKEND_DIR.
BACKEND_DIR="${PROJECT_ROOT}/backend"

log "Installing maturin in venv..."
python -m pip install --upgrade maturin

if [ -f "${BACKEND_DIR}/Cargo.toml" ]; then
  log "Building + installing PyO3 module from ./backend (maturin develop --release)..."
  pushd "$BACKEND_DIR" >/dev/null
  maturin develop --release
  popd >/dev/null
elif [ -f "${PROJECT_ROOT}/Cargo.toml" ]; then
  log "Building + installing PyO3 module from project root (maturin develop --release)..."
  maturin develop --release
else
  log "WARNING: Could not find Cargo.toml in ./backend or project root."
  log "wifi_backend will not be built. Adjust BACKEND_DIR in install.sh."
fi

# ---- 6) Sanity checks ----
log "Sanity checks (imports + PATH)..."
python - <<'PY'
import sys
print("Python:", sys.executable)

from PySide6.QtWidgets import QApplication
print("PySide6: OK")

try:
    import wifi_backend
    print("wifi_backend: OK")
except Exception as e:
    print("wifi_backend: FAILED ->", repr(e))
PY

log "Install complete."
echo "You are now in an ACTIVE virtual environment."
echo "Run: python3 main.py"
echo

# ---- 7) Keep venv active for the user ----
exec "$SHELL"

