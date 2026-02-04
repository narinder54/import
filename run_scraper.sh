#!/bin/bash
# Wrapper script to run Python with virtual environment

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create temp directory for Playwright in project
TEMP_DIR="${DIR}/temp"
mkdir -p "$TEMP_DIR"
chmod 777 "$TEMP_DIR"

# Set environment variables for Playwright
export TMPDIR="$TEMP_DIR"
export TEMP="$TEMP_DIR"
export TMP="$TEMP_DIR"
export PLAYWRIGHT_BROWSERS_PATH="${DIR}/venv/playwright-browsers"

# Use virtual environment Python
"${DIR}/venv/bin/python3" "$@"
