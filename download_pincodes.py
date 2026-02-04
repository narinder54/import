#!/usr/bin/env python3
"""
Download and organize India PIN codes by state
Source: https://github.com/deep5050/indian-pincodes-database
"""

import json
import urllib.request
import ssl
from collections import defaultdict

# URL for the PIN codes database
DATA_URL = "https://raw.githubusercontent.com/deep5050/indian-pincodes-database/master/data.json"

def download_pincodes():
    """Download PIN codes from GitHub"""
    print("Downloading PIN codes database from GitHub...")
    print("This may take a moment (file is ~8MB)...")

    # Create SSL context to handle certificate issues
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(DATA_URL, context=ctx) as response:
            # Use utf-8-sig to handle BOM
            data = json.loads(response.read().decode('utf-8-sig'))
            print(f"✓ Downloaded successfully!")
            return data
    except Exception as e:
        print(f"✗ Error downloading: {e}")
        return None

def organize_by_state(data):
    """Organize PIN codes by state"""
    pincodes_by_state = defaultdict(list)

    records = data.get('Sheet1', [])
    print(f"Processing {len(records)} PIN code records...")

    seen_pincodes = defaultdict(set)  # Track unique pincodes per state

    for record in records:
        state = record.get('State', '').strip()
        pincode = str(record.get('Pincode', '')).strip()
        city = record.get('City', '').strip()
        district = record.get('District', '').strip()
        post_office = record.get('PostOfficeName', '').strip()

        if not state or not pincode or len(pincode) != 6:
            continue

        # Skip if we've already added this pincode for this state
        if pincode in seen_pincodes[state]:
            continue

        seen_pincodes[state].add(pincode)

        pincodes_by_state[state].append({
            'pincode': pincode,
            'city': city,
            'district': district,
            'area': post_office
        })

    # Sort pincodes within each state
    for state in pincodes_by_state:
        pincodes_by_state[state].sort(key=lambda x: x['pincode'])

    return dict(pincodes_by_state)

def create_simple_format(pincodes_by_state):
    """Create a simpler format with just pincodes and area names per state"""
    simple_format = {}

    for state, pincodes in pincodes_by_state.items():
        simple_format[state] = []
        for p in pincodes:
            # Create a search-friendly entry
            entry = {
                'pincode': p['pincode'],
                'area': p['area'],
                'city': p['city'],
                'district': p['district']
            }
            simple_format[state].append(entry)

    return simple_format

def print_summary(pincodes_by_state):
    """Print summary of PIN codes by state"""
    print("\n" + "="*50)
    print("PIN CODES SUMMARY BY STATE")
    print("="*50)

    total = 0
    for state in sorted(pincodes_by_state.keys()):
        count = len(pincodes_by_state[state])
        total += count
        print(f"{state}: {count} unique PIN codes")

    print("="*50)
    print(f"TOTAL: {total} unique PIN codes across {len(pincodes_by_state)} states/UTs")
    print("="*50)

def main():
    # Download data
    data = download_pincodes()
    if not data:
        return

    # Organize by state
    pincodes_by_state = organize_by_state(data)

    # Print summary
    print_summary(pincodes_by_state)

    # Save detailed format
    output_file = 'pincodes_by_state.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pincodes_by_state, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved to {output_file}")

    # Also create a simpler list format (just pincodes per state)
    simple_pincodes = {}
    for state, pincodes in pincodes_by_state.items():
        simple_pincodes[state] = [p['pincode'] for p in pincodes]

    simple_file = 'pincodes_simple.json'
    with open(simple_file, 'w', encoding='utf-8') as f:
        json.dump(simple_pincodes, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved simple format to {simple_file}")

    print("\nDone! You can now run the batch scraper with PIN code support.")

if __name__ == '__main__':
    main()
