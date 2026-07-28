#!/usr/bin/env bash
# Resolve DISPLAY + XAUTHORITY for the logged-in graphical session, then run typer.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="$ROOT/.venv/bin/python"
APP="$ROOT/typer.py"

if [[ ! -x "$PY" ]]; then
  echo "Missing venv at $PY — run ./setup.sh first" >&2
  exit 1
fi

uid="$(id -u)"

find_display() {
  if [[ -n "${DISPLAY:-}" ]]; then
    echo "$DISPLAY"
    return
  fi
  for d in :1 :0 :2; do
    if [[ -S "/tmp/.X11-unix/X${d#:}" ]]; then
      echo "$d"
      return
    fi
  done
}

find_xauth() {
  if [[ -n "${XAUTHORITY:-}" && -f "${XAUTHORITY}" ]]; then
    echo "$XAUTHORITY"
    return
  fi
  # GNOME/GDM on Ubuntu (most common)
  for p in \
    "/run/user/${uid}/gdm/Xauthority" \
    "/run/user/${uid}/.mutter-Xwaylandauth"* \
    "${HOME}/.Xauthority"
  do
    # shellcheck disable=SC2086
    for f in $p; do
      if [[ -f "$f" ]]; then
        echo "$f"
        return
      fi
    done
  done
}

export DISPLAY="$(find_display)"
export XAUTHORITY="$(find_xauth)"

if [[ -z "${DISPLAY}" ]]; then
  echo "No DISPLAY found — is a desktop session running?" >&2
  exit 1
fi

# Wait until X accepts connections (service can start before X is ready)
ok=0
for _ in $(seq 1 40); do
  if "$PY" -c "import os; from Xlib import display; display.Display(os.environ['DISPLAY'])" 2>/dev/null; then
    ok=1
    break
  fi
  # fallback without python-xlib: try xdpyinfo if present
  if command -v xdpyinfo >/dev/null 2>&1 && xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 0.5
done

echo "human-typer starting"
echo "  DISPLAY=$DISPLAY"
echo "  XAUTHORITY=${XAUTHORITY:-<empty>}"
echo "  ARGS=${HUMAN_TYPER_ARGS:-<defaults from typer.py>}"

if [[ "$ok" -ne 1 ]]; then
  echo "WARNING: could not verify X connection; trying anyway" >&2
fi

# Extra args via HUMAN_TYPER_ARGS, e.g. "--delay 2.5 --wpm 58 --mistake-prob 0.02"
# shellcheck disable=SC2086
exec "$PY" "$APP" ${HUMAN_TYPER_ARGS:-}
