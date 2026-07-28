#!/usr/bin/env bash
# Quick diagnosis: is F8 the problem, or is the service missing X11?
set -euo pipefail

echo "=== human-typer doctor ==="
echo
echo "1) Session"
echo "   DISPLAY=${DISPLAY:-<empty>}"
echo "   XAUTHORITY=${XAUTHORITY:-<empty>}"
echo "   XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-<empty>}"
echo

echo "2) Service status"
systemctl --user status human-typer --no-pager -l || true
echo

echo "3) Recent logs"
journalctl --user -u human-typer -n 30 --no-pager || true
echo

echo "4) Is something else already running typer?"
pgrep -af 'typer.py|human-typer/run' || echo "   (none)"
echo

echo "5) F8 system bindings (GNOME)"
if command -v gsettings >/dev/null 2>&1; then
  gsettings list-recursively org.gnome.desktop.wm.keybindings 2>/dev/null | grep -i f8 || echo "   No WM F8 binding found"
  gsettings list-recursively org.gnome.settings-daemon.plugins.media-keys 2>/dev/null | grep -i f8 || echo "   No media-key F8 binding found"
else
  echo "   gsettings not available"
fi
echo
echo "Note: plain F8 is usually free on Ubuntu. Service failures are almost"
echo "always missing DISPLAY/XAUTHORITY — check logs above for those lines."
echo
echo "Fix / refresh:"
echo "  cd ~/Desktop/MY_STUFF/human-typer && ./install-service.sh"
echo "  journalctl --user -u human-typer -f"
