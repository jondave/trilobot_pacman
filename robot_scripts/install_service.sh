#!/usr/bin/env bash
# Install trilobot-websocket.service for this checkout and start it.
#
#   sudo ./install_service.sh
#
# Uses this folder's real path, the user who ran sudo, and python3 from a
# .venv in the repo or robot_scripts/ if one exists (override with PYTHON=...).
# Also removes the old trilobot-robot.service if it is installed.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
user="${SERVICE_USER:-${SUDO_USER:-pi}}"
python="${PYTHON:-}"
if [[ -z "$python" ]]; then
  for candidate in "$here/.venv/bin/python3" "$here/../.venv/bin/python3"; do
    if [[ -x "$candidate" ]]; then
      python="$(cd "$(dirname "$candidate")" && pwd -P)/python3"
      break
    fi
  done
fi
python="${python:-$(command -v python3)}"

unit=/etc/systemd/system/trilobot-websocket.service
sed -e "s|@USER@|$user|g" -e "s|@ROBOT_SCRIPTS@|$here|g" -e "s|@PYTHON@|$python|g" \
  "$here/trilobot-websocket.service" > "$unit"
echo "Wrote $unit (user $user, folder $here, python $python)"

old=/etc/systemd/system/trilobot-robot.service
if [[ -e "$old" ]]; then
  systemctl disable --now trilobot-robot.service || true
  rm -f "$old"
  echo "Removed the old trilobot-robot.service"
fi

systemctl daemon-reload
systemctl enable trilobot-websocket.service
systemctl restart trilobot-websocket.service
systemctl --no-pager --lines=5 status trilobot-websocket.service || true
echo "Follow the logs with: journalctl -u trilobot-websocket -f"
