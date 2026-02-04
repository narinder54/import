#!/bin/bash
# Background scrape job runner
# This runs as YOUR user, not as Apache, avoiding the SIGTRAP issue

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if a job file was provided
if [ -z "$1" ]; then
    echo "Usage: $0 <job_file>"
    exit 1
fi

JOB_FILE="$1"

if [ ! -f "$JOB_FILE" ]; then
    echo "Job file not found: $JOB_FILE"
    exit 1
fi

# Read job parameters
source "$JOB_FILE"

# Run the scraper
cd "$DIR"
./run_scraper.sh google_maps_scraper.py "$QUERY" "$LOCATION" "$MAX_RESULTS" "$HEADLESS" > "${JOB_FILE}.log" 2>&1

# Mark job as complete
echo "COMPLETED" > "${JOB_FILE}.status"
