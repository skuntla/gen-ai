#!/usr/bin/env bash
# Run Phase 03 RAG evals with the project venv Python.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PROMPTFOO_PYTHON="${ROOT}/.venv/bin/python"
cd "$ROOT"
exec promptfoo eval -c evals/promptfooconfig.yaml "$@"
