#!/usr/bin/env bash
# Install human-typer as a systemd --user service (starts with your desktop login).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
UNIT_SRC="$ROOT/human-typer.service"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_DST="$UNIT_DIR/human-typer.service"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Do NOT run this as root. Run as your normal user (vk_lx)." >&2
  exit 1
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "venv missing — run: cd \"$ROOT\" && ./setup.sh" >&2
  exit 1
fi

chmod +x "$ROOT/run.sh" "$ROOT/setup.sh" "$ROOT/install-service.sh"

mkdir -p "$UNIT_DIR"
cp "$UNIT_SRC" "$UNIT_DST"

# Ensure systemd user bus can see DISPLAY after graphical login
systemctl --user import-environment DISPLAY XAUTHORITY 2>/dev/null || true

# Drop old graphical-session-only enable if present
systemctl --user disable human-typer.service 2>/dev/null || true

systemctl --user daemon-reload
systemctl --user enable human-typer.service
# Always restart so re-running this script picks up unit + code updates
systemctl --user restart human-typer.service

echo
echo "Installed / updated and restarted."
echo "  Status : systemctl --user status human-typer"
echo "  Logs   : journalctl --user -u human-typer -f"
echo "  Stop   : systemctl --user stop human-typer"
echo "  Disable: systemctl --user disable --now human-typer"
echo
echo "Re-run this script anytime to replace the unit file and restart."
echo "If you only edited typer.py, this also works — or just:"
echo "  systemctl --user restart human-typer"
echo
echo "It will start again automatically on each desktop login."
echo "Hotkey: F8 (press outside browser, then focus the text box during countdown)."
