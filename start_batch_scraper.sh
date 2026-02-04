#!/bin/bash
# Start the automated batch scraper

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Starting Automated Batch Scraper..."
echo "Press Ctrl+C to pause (state will be saved)"
echo ""

cd "$DIR"
./run_scraper.sh batch_scraper.py
