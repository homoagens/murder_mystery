#!/bin/bash
cd "$(dirname "$0")"
(sleep 2 && xdg-open http://localhost:7860 2>/dev/null || open http://localhost:7860 2>/dev/null) &
./venv/bin/python -m app.run
