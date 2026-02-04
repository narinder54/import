#!/usr/bin/env python3
"""
Geocode all Indian cities and save coordinates to JSON file
Uses Nominatim (OpenStreetMap) - free and unlimited for reasonable use
"""

import json
import time
import requests
from typing import Dict, List, Tuple, Optional

def geocode_city(city: str, state: str) -> Optional[Tuple[float, float]]:
    """
    Geocode a city to get lat/long coordinates
    Returns: (latitude, longitude) or None if not found
    """
    try:
        # Nominatim API (OpenStreetMap)
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{city}, {state}, India",
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'GoogleMapsScraperGeocoder/1.0'
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data and len(data) > 0:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return (lat, lon)
        else:
            print(f"  ⚠️  No coordinates found for {city}, {state}")
            return None

    except Exception as e:
        print(f"  ✗ Error geocoding {city}, {state}: {str(e)}")
        return None


def geocode_all_cities():
    """Geocode all cities from cities_by_state.json"""

    print("=" * 60)
    print("🌍 Geocoding Indian Cities")
    print("=" * 60)

    # Load cities
    with open('cities_by_state.json', 'r', encoding='utf-8') as f:
        cities_by_state = json.load(f)

    # Calculate total
    total_cities = sum(len(cities) for cities in cities_by_state.values())
    print(f"\n📊 Total cities to geocode: {total_cities}")
    print(f"📊 Total states: {len(cities_by_state)}")

    # Check if we have partial progress
    try:
        with open('city_coordinates.json', 'r', encoding='utf-8') as f:
            coordinates = json.load(f)
        print(f"✓ Loaded {len(coordinates)} existing coordinates")
    except FileNotFoundError:
        coordinates = {}
        print("✓ Starting fresh")

    print("\n🚀 Starting geocoding...")
    print("=" * 60)

    processed = len(coordinates)
    errors = 0

    for state, cities in cities_by_state.items():
        print(f"\n📍 State: {state} ({len(cities)} cities)")

        for city in cities:
            # Create unique key
            key = f"{city}, {state}"

            # Skip if already geocoded
            if key in coordinates:
                continue

            # Geocode
            result = geocode_city(city, state)

            if result:
                coordinates[key] = {
                    'city': city,
                    'state': state,
                    'lat': result[0],
                    'lng': result[1]
                }
                print(f"  ✓ {city}: {result[0]:.4f}, {result[1]:.4f}")
            else:
                errors += 1

            processed += 1

            # Save progress every 10 cities
            if processed % 10 == 0:
                with open('city_coordinates.json', 'w', encoding='utf-8') as f:
                    json.dump(coordinates, f, indent=2, ensure_ascii=False)
                print(f"\n💾 Progress saved: {processed}/{total_cities} ({processed/total_cities*100:.1f}%)")

            # Respectful delay (Nominatim requirement: max 1 request per second)
            time.sleep(1.1)

    # Final save
    with open('city_coordinates.json', 'w', encoding='utf-8') as f:
        json.dump(coordinates, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("✅ GEOCODING COMPLETE")
    print("=" * 60)
    print(f"✓ Total processed: {processed}")
    print(f"✓ Successful: {len(coordinates)}")
    print(f"✗ Errors: {errors}")
    print(f"✓ Success rate: {len(coordinates)/total_cities*100:.1f}%")
    print(f"\n💾 Saved to: city_coordinates.json")
    print("=" * 60)


if __name__ == "__main__":
    try:
        geocode_all_cities()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("💾 Progress has been saved to city_coordinates.json")
        print("   Run script again to continue from where you left off")
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
