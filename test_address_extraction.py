#!/usr/bin/env python3
"""
Test Address Extraction
Demonstrates the improved city, state, and pincode extraction
"""

import json
import re

# Load cities database
with open('cities_by_state.json', 'r', encoding='utf-8') as f:
    cities_by_state = json.load(f)

def extract_pincode(address):
    """Extract PIN code from address"""
    if not address:
        return None
    match = re.search(r'\b\d{6}\b', address)
    return match.group(0) if match else None

def extract_city_from_address(address):
    """Extract city name from address using proper parsing logic"""
    if not address:
        return None

    # Split address by comma and clean up parts
    parts = [part.strip() for part in address.split(',')]
    if len(parts) < 3:
        return None

    # Address format: ..., City, State Pincode
    # Get last part (should be "State Pincode" or just "Pincode")
    last_part = parts[-1]

    # Remove pincode from last part to get potential state
    last_part_cleaned = re.sub(r'\b\d{6}\b', '', last_part).strip()

    # If last part had both state and pincode, city is second-to-last
    # If last part was just pincode, state is second-to-last and city is third-to-last
    if last_part_cleaned:
        # Format: ..., City, State Pincode
        potential_city = parts[-2] if len(parts) >= 2 else None
    else:
        # Format: ..., City, State, Pincode
        potential_city = parts[-3] if len(parts) >= 3 else None

    if not potential_city:
        return None

    potential_city = potential_city.strip()

    # Validate city exists in our database
    for state_name, cities in cities_by_state.items():
        for city_name in cities:
            if potential_city.lower() == city_name.lower():
                return city_name
            # Also check if potential_city contains the city name
            if city_name.lower() in potential_city.lower():
                return city_name

    return None

def extract_state_from_address(address):
    """Extract state name from address using proper parsing logic"""
    if not address:
        return None

    # Split address by comma and clean up parts
    parts = [part.strip() for part in address.split(',')]
    if len(parts) < 2:
        return None

    # Address format: ..., City, State Pincode OR ..., City, State, Pincode
    # Get last part
    last_part = parts[-1]

    # Remove pincode from last part to get potential state
    last_part_cleaned = re.sub(r'\b\d{6}\b', '', last_part).strip()

    # Determine which part contains state
    if last_part_cleaned:
        # Format: ..., City, State Pincode
        potential_state = last_part_cleaned
    else:
        # Format: ..., City, State, Pincode - state is second-to-last
        potential_state = parts[-2] if len(parts) >= 2 else None

    if not potential_state:
        return None

    potential_state_lower = potential_state.lower()

    # State abbreviations and alternate names
    state_mappings = {
        'mh': 'Maharashtra', 'maharashtra': 'Maharashtra',
        'ka': 'Karnataka', 'karnataka': 'Karnataka',
        'tn': 'Tamil Nadu', 'tamil nadu': 'Tamil Nadu', 'tamilnadu': 'Tamil Nadu',
        'tg': 'Telangana', 'telangana': 'Telangana',
        'ap': 'Andhra Pradesh', 'andhra pradesh': 'Andhra Pradesh',
        'gj': 'Gujarat', 'gujarat': 'Gujarat',
        'rj': 'Rajasthan', 'rajasthan': 'Rajasthan',
        'up': 'Uttar Pradesh', 'uttar pradesh': 'Uttar Pradesh',
        'mp': 'Madhya Pradesh', 'madhya pradesh': 'Madhya Pradesh',
        'pb': 'Punjab', 'punjab': 'Punjab',
        'hr': 'Haryana', 'haryana': 'Haryana',
        'wb': 'West Bengal', 'west bengal': 'West Bengal',
        'kl': 'Kerala', 'kerala': 'Kerala',
        'or': 'Odisha', 'odisha': 'Odisha', 'orissa': 'Odisha',
        'jh': 'Jharkhand', 'jharkhand': 'Jharkhand',
        'as': 'Assam', 'assam': 'Assam',
        'br': 'Bihar', 'bihar': 'Bihar',
        'cg': 'Chhattisgarh', 'chhattisgarh': 'Chhattisgarh',
        'ga': 'Goa', 'goa': 'Goa',
        'hp': 'Himachal Pradesh', 'himachal pradesh': 'Himachal Pradesh',
        'jk': 'Jammu and Kashmir', 'jammu and kashmir': 'Jammu and Kashmir',
        'dl': 'Delhi', 'delhi': 'Delhi', 'new delhi': 'Delhi',
        'ch': 'Chandigarh', 'chandigarh': 'Chandigarh',
        'py': 'Puducherry', 'puducherry': 'Puducherry', 'pondicherry': 'Puducherry',
        'uk': 'Uttarakhand', 'uttarakhand': 'Uttarakhand',
    }

    # Check exact match first
    for key, state_name in state_mappings.items():
        if potential_state_lower == key or potential_state_lower == key.replace(' ', ''):
            return state_name

    # Check if state name is contained in the potential state part
    for state_name in cities_by_state.keys():
        if state_name.lower() in potential_state_lower:
            return state_name

    return None

# Test addresses
test_addresses = [
    "AMC 1, 581, Ana Sagar Circular Rd, above Lapinozz Pizza, Shantipura, Anand Nagar, Ajmer, Rajasthan 305001",
    "123, MG Road, Brigade Road, Bangalore, Karnataka 560001",
    "45, Park Street, Sector 17, Chandigarh 160017",
    "Plot 456, Near Bus Stand, Hisar, Haryana, 125001",
    "Building A, Street 5, Mumbai, Maharashtra, 400001"
]

print("\n" + "="*80)
print("🧪 Testing Address Extraction")
print("="*80 + "\n")

for idx, address in enumerate(test_addresses, 1):
    print(f"Test {idx}:")
    print(f"📍 Address: {address}")
    print(f"  🏙️  City: {extract_city_from_address(address)}")
    print(f"  🗺️  State: {extract_state_from_address(address)}")
    print(f"  📮 Pincode: {extract_pincode(address)}")
    print()

print("="*80)
print("✅ Test complete!\n")
