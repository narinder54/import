#!/bin/bash
# Quick script to check geocoding progress

COORDS_FILE="city_coordinates.json"
TOTAL=1202

if [ ! -f "$COORDS_FILE" ]; then
    echo "❌ City coordinates file not found"
    exit 1
fi

CURRENT=$(cat "$COORDS_FILE" | grep '"city":' | wc -l | tr -d ' ')
PERCENT=$((CURRENT * 100 / TOTAL))

echo "📍 Geocoding Progress"
echo "====================="
echo "✓ Cities geocoded: $CURRENT / $TOTAL"
echo "📊 Progress: $PERCENT%"

if [ $CURRENT -eq $TOTAL ]; then
    echo "✅ COMPLETE!"
else
    REMAINING=$((TOTAL - CURRENT))
    EST_MIN=$((REMAINING * 11 / 10 / 60))
    echo "⏳ Remaining: $REMAINING cities (~$EST_MIN minutes)"
fi
