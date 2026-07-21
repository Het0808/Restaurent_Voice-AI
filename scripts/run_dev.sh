#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}src"
exec uvicorn restaurant_voice_ai.main:app --reload
