#!/usr/bin/env python3
"""
Reset scraper state to a specific point
"""

import json
import sys

def reset_state(target_state=None):
    """Reset scraper state"""

    # Load current config and cities
    with open('batch_config.json', 'r') as f:
        config = json.load(f)

    with open('cities_by_state.json', 'r') as f:
        cities = json.load(f)

    states_list = config.get('states_to_scrape', list(cities.keys()))

    if target_state:
        # Reset to specific state
        if target_state not in states_list:
            print(f"❌ State '{target_state}' not found in states_to_scrape list")
            print(f"\nAvailable states:")
            for i, s in enumerate(states_list):
                print(f"  {i+1}. {s}")
            return

        state_index = states_list.index(target_state)
        first_city = cities[target_state][0]

        print(f"🔄 Resetting to: {target_state} > {first_city}")
    else:
        # Reset to very beginning
        target_state = states_list[0]
        state_index = 0
        first_city = cities[target_state][0]

        print(f"🔄 Resetting to beginning: {target_state} > {first_city}")

    # Create reset state
    state = {
        "last_query_index": 0,
        "last_state_index": state_index,
        "last_city_index": 0,
        "current_state": target_state,
        "current_city": first_city,
        "completed_combinations": [],
        "total_scraped": 0,
        "total_saved": 0,
        "last_run_timestamp": "",
        "status": "paused",
        "captcha_detected": False,
        "error_count": 0
    }

    # Save
    with open('scraper_state.json', 'w') as f:
        json.dump(state, f, indent=2)

    print("✅ State reset successfully!")
    print(f"\n📍 Will start from:")
    print(f"   State: {target_state}")
    print(f"   City: {first_city}")
    print(f"   Query: {config['queries'][0]}")
    print(f"\n🚀 Run: ./start_batch_scraper.sh")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        state_name = ' '.join(sys.argv[1:])
        reset_state(state_name)
    else:
        print("Usage:")
        print("  python3 reset_state.py                 # Reset to very beginning")
        print("  python3 reset_state.py 'Rajasthan'     # Reset to specific state")
        print("  python3 reset_state.py 'Tamil Nadu'    # Reset to specific state")
        print()

        # Load and show states
        with open('batch_config.json', 'r') as f:
            config = json.load(f)
        states_list = config.get('states_to_scrape', [])

        print(f"Available states ({len(states_list)}):")
        for i, s in enumerate(states_list, 1):
            print(f"  {i:2d}. {s}")
        print()

        # Ask for confirmation
        choice = input("Reset to beginning? (y/N): ")
        if choice.lower() == 'y':
            reset_state()
        else:
            print("❌ Cancelled")
