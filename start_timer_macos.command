#!/bin/zsh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_SCRIPT="$SCRIPT_DIR/focus_break_timer.py"

pick_python() {
  local candidates=(
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"
    "/usr/local/bin/python3"
    "/usr/bin/python3"
  )
  for p in "${candidates[@]}"; do
    if [[ -x "$p" ]] && "$p" -c "import tkinter" >/dev/null 2>&1; then
      echo "$p"
      return
    fi
  done
  echo "python3"
}

PYTHON_BIN="$(pick_python)"
exec "$PYTHON_BIN" "$APP_SCRIPT"
