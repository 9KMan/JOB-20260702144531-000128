#!/usr/bin/env bash
# Bash wrapper for run_pipeline.py
# Usage: bash run_pipeline.sh
#
# This script:
#   1. Loads environment variables from .env if present
#   2. Runs the Python pipeline entry point
#   3. Exits with the pipeline's exit code

set -euo pipefail

# Resolve script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env file if it exists
if [[ -f "${SCRIPT_DIR}/.env" ]]; then
    echo "Loading environment from ${SCRIPT_DIR}/.env"
    set -a
    # shellcheck disable=SC1090
    source "${SCRIPT_DIR}/.env"
    set +a
fi

# Run the pipeline
echo "Starting pipeline..."
exec python3 "${SCRIPT_DIR}/run_pipeline.py" "$@"