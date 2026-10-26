#!/usr/bin/env bash
# Huntly Execution Wrapper

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
VENV="$DIR/.venv"

if [ -f "$VENV/bin/python" ]; then
    PYTHON="$VENV/bin/python"
else
    PYTHON="python3"
fi

export PYTHONPATH="$DIR:$PYTHONPATH"

if [ $# -eq 0 ]; then
    exec "$PYTHON" -m huntly.cli ui
else
    exec "$PYTHON" -m huntly.cli "$@"
fi
