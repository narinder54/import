#!/usr/bin/env python3
"""
FAST Geocoding with parallel requests
Uses multiple threads to geocode cities much faster
"""

import json
import time
import requests
import threading
from queue import Queue
from typing import Dict, Optional, Tuple

class FastGeocoder:
    def __init__(self, num_threads=10, delay_between_requests=0.1):
        """
        Initialize fast geocoder

        Args:
            num_threads: Number of parallel threads (default 10)
            delay_between_requests: Delay in seconds between requests per thread (default 0.1)
        """
        self.num_threads = num_threads
        self.delay = delay_between_requests
        self.coordinates = {}
        self.lock = threading.Lock()
        self.errors = 0
        self.processed = 0
        self.total = 0

    def geocode_city(self, city: str, state: str) -> Optional[Tuple[float, float]]:
        """Geocode a single city"""
        try:
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
                return None

        except Exception as e:
            return None

    def worker(self, queue):
        """Worker thread that processes cities from queue"""
        while True:
            item = queue.get()
            if item is None:
                break

            city, state, key = item

            # Check if already processed
            with self.lock:
                if key in self.coordinates:
                    queue.task_done()
                    continue

            # Geocode
            result = self.geocode_city(city, state)

            # Save result
            with self.lock:
                if result:
                    self.coordinates[key] = {
                        'city': city,
                        'state': state,
                        'lat': result[0],
                        'lng': result[1]
                    }
                    print(f"  ✓ {city}, {state}: {result[0]:.4f}, {result[1]:.4f}", flush=True)
                else:
                    self.errors += 1
                    print(f"  ✗ {city}, {state}: not found", flush=True)

                self.processed += 1

                # Save progress every 50 cities
                if self.processed % 50 == 0:
                    self.save_progress()
                    print(f"\n💾 Progress: {self.processed}/{self.total} ({self.processed/self.total*100:.1f}%)\n", flush=True)

            # Small delay to be respectful
            time.sleep(self.delay)

            queue.task_done()

    def save_progress(self):
        """Save current progress to file"""
        with open('city_coordinates.json', 'w', encoding='utf-8') as f:
            json.dump(self.coordinates, f, indent=2, ensure_ascii=False)

    def geocode_all(self):
        """Geocode all cities using multiple threads"""
        print("=" * 60)
        print(f"🚀 FAST Geocoding with {self.num_threads} parallel threads")
        print("=" * 60)

        # Load cities
        with open('cities_by_state.json', 'r', encoding='utf-8') as f:
            cities_by_state = json.load(f)

        # Load existing coordinates
        try:
            with open('city_coordinates.json', 'r', encoding='utf-8') as f:
                self.coordinates = json.load(f)
            print(f"✓ Loaded {len(self.coordinates)} existing coordinates")
        except FileNotFoundError:
            self.coordinates = {}
            print("✓ Starting fresh")

        # Calculate total
        self.total = sum(len(cities) for cities in cities_by_state.values())
        print(f"📊 Total cities: {self.total}")
        print(f"📊 Already done: {len(self.coordinates)}")
        print(f"📊 Remaining: {self.total - len(self.coordinates)}")

        # Create queue
        queue = Queue()

        # Add all cities to queue
        for state, cities in cities_by_state.items():
            for city in cities:
                key = f"{city}, {state}"
                if key not in self.coordinates:
                    queue.put((city, state, key))

        print(f"\n🚀 Starting {self.num_threads} worker threads...")
        print("=" * 60 + "\n")

        # Start worker threads
        threads = []
        for i in range(self.num_threads):
            t = threading.Thread(target=self.worker, args=(queue,))
            t.start()
            threads.append(t)

        # Wait for all tasks to complete
        queue.join()

        # Stop workers
        for i in range(self.num_threads):
            queue.put(None)
        for t in threads:
            t.join()

        # Final save
        self.save_progress()

        print("\n" + "=" * 60)
        print("✅ GEOCODING COMPLETE")
        print("=" * 60)
        print(f"✓ Total processed: {self.processed}")
        print(f"✓ Successful: {len(self.coordinates)}")
        print(f"✗ Errors: {self.errors}")
        print(f"✓ Success rate: {len(self.coordinates)/self.total*100:.1f}%")
        print(f"\n💾 Saved to: city_coordinates.json")
        print("=" * 60)


if __name__ == "__main__":
    try:
        # Create geocoder with 10 parallel threads
        # Adjust num_threads (5-20) and delay (0.05-0.2) based on your needs
        geocoder = FastGeocoder(num_threads=10, delay_between_requests=0.1)
        geocoder.geocode_all()

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        geocoder.save_progress()
        print("💾 Progress has been saved to city_coordinates.json")
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
