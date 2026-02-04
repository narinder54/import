#!/bin/bash
# Live monitoring of geocoding progress

echo "🔄 Monitoring geocoding progress (Ctrl+C to stop)"
echo "=================================================="
echo

while true; do
    clear
    date
    echo
    ./check_geocode_progress.sh
    echo
    echo "Recent activity:"
    tail -10 geocode_fast.log 2>/dev/null | grep -E "✓|✗" | tail -5
    echo
    echo "Press Ctrl+C to stop monitoring"
    sleep 5
done
