#!/usr/bin/env python3
"""
Update Address Fields Script
Updates city, state, and pincode for all existing records based on their addresses
"""

import json
import re
import mysql.connector
from mysql.connector import Error

class AddressUpdater:
    def __init__(self):
        # Load cities database
        with open('cities_by_state.json', 'r', encoding='utf-8') as f:
            self.cities_by_state = json.load(f)

        # Database config
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'immigration_agents_db'
        }

    def extract_pincode(self, address):
        """Extract PIN code from address"""
        if not address:
            return None
        match = re.search(r'\b\d{6}\b', address)
        return match.group(0) if match else None

    def extract_city_from_address(self, address):
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
        for state_name, cities in self.cities_by_state.items():
            for city_name in cities:
                if potential_city.lower() == city_name.lower():
                    return city_name
                # Also check if potential_city contains the city name
                if city_name.lower() in potential_city.lower():
                    return city_name

        return None

    def extract_state_from_address(self, address):
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
        for state_name in self.cities_by_state.keys():
            if state_name.lower() in potential_state_lower:
                return state_name

        return None

    def update_all_records(self):
        """Update all records in database"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)

            # Get all records with addresses
            cursor.execute("SELECT id, business_name, address, city, state, pincode FROM agents WHERE address IS NOT NULL AND address != ''")
            records = cursor.fetchall()

            print(f"📊 Found {len(records)} records with addresses")
            print(f"{'='*80}\n")

            updated_count = 0
            skipped_count = 0
            error_count = 0

            for idx, record in enumerate(records, 1):
                record_id = record['id']
                business_name = record['business_name']
                address = record['address']
                old_city = record['city']
                old_state = record['state']
                old_pincode = record['pincode']

                # Extract new values
                new_city = self.extract_city_from_address(address)
                new_state = self.extract_state_from_address(address)
                new_pincode = self.extract_pincode(address)

                # Check if any value changed
                city_changed = new_city and new_city != old_city
                state_changed = new_state and new_state != old_state
                pincode_changed = new_pincode and new_pincode != old_pincode

                if city_changed or state_changed or pincode_changed:
                    print(f"[{idx}/{len(records)}] Updating: {business_name[:50]}")
                    print(f"  📍 Address: {address[:80]}...")

                    if city_changed:
                        print(f"  🏙️  City: {old_city} → {new_city}")
                    if state_changed:
                        print(f"  🗺️  State: {old_state} → {new_state}")
                    if pincode_changed:
                        print(f"  📮 Pincode: {old_pincode} → {new_pincode}")

                    # Update record
                    try:
                        update_sql = """
                            UPDATE agents
                            SET city = %s, state = %s, pincode = %s
                            WHERE id = %s
                        """
                        cursor.execute(update_sql, (
                            new_city or old_city,
                            new_state or old_state,
                            new_pincode or old_pincode,
                            record_id
                        ))
                        conn.commit()
                        updated_count += 1
                        print(f"  ✅ Updated successfully\n")
                    except Exception as e:
                        error_count += 1
                        print(f"  ❌ Error updating: {str(e)}\n")
                else:
                    skipped_count += 1
                    if idx % 50 == 0:
                        print(f"[{idx}/{len(records)}] No changes needed, continuing...")

            cursor.close()
            conn.close()

            # Summary
            print(f"\n{'='*80}")
            print(f"📊 Update Summary:")
            print(f"{'='*80}")
            print(f"  ✅ Updated: {updated_count} records")
            print(f"  ⏭️  Skipped (no changes): {skipped_count} records")
            print(f"  ❌ Errors: {error_count} records")
            print(f"  📝 Total processed: {len(records)} records")
            print(f"{'='*80}\n")

        except Error as e:
            print(f"❌ Database error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("\n🔄 Starting Address Field Update")
    print("="*80)
    print("This script will update city, state, and pincode for all records")
    print("based on their addresses using proper parsing logic.")
    print("="*80 + "\n")

    updater = AddressUpdater()
    updater.update_all_records()

    print("✅ Update complete!\n")
