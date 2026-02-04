#!/usr/bin/env python3
"""
Simplified Google Maps Scraper - City Mode
Searches by city instead of pincode for efficiency
"""

import sys
import json
import time
import random
import pymysql
from playwright.sync_api import sync_playwright
import re

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'immigration_agents_db',
    'charset': 'utf8mb4'
}


class BatchScraper:
    def __init__(self, config_file='batch_config.json', state_file='scraper_state.json', cities_file='cities_by_state.json'):
        self.config_file = config_file
        self.state_file = state_file
        self.cities_file = cities_file

        # Load configuration
        self.config = self.load_json(config_file)
        self.state = self.load_json(state_file)

        # Load cities data
        try:
            self.cities_by_state = self.load_json(cities_file)
            total_cities = sum(len(cities) for cities in self.cities_by_state.values())
            print(f"✓ Loaded {total_cities} cities across {len(self.cities_by_state)} states")
        except FileNotFoundError:
            print("⚠️  Cities file not found!")
            sys.exit(1)

        self.states_to_scrape = self.config.get('states_to_scrape', list(self.cities_by_state.keys()))
        self.results = []

    def load_json(self, filename):
        """Load JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {str(e)}")
            sys.exit(1)

    def save_state(self):
        """Save current state to file"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {str(e)}")

    def extract_phone(self, text):
        """Extract phone number from text"""
        if not text:
            return None
        text = text.replace('\n', ' ').replace('\t', ' ')
        patterns = [
            r'\+91[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d',
            r'\+91[\s-]?\d{10}',
            r'\+91[\s-]?\d{5}[\s-]?\d{5}',
            r'0\d{2,4}[\s\-\.]*\d{6,8}',
            r'\d{10}',
            r'\d{5}[\s-]\d{5}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0).strip()
                phone = re.sub(r'[\s\-\.]+', ' ', phone).strip()
                return phone
        return None

    def extract_pincode(self, address):
        """Extract PIN code from address"""
        if not address:
            return None
        match = re.search(r'\b\d{6}\b', address)
        return match.group(0) if match else None

    def extract_city_from_address(self, address):
        """Extract city name from address"""
        if not address:
            return None
        parts = [part.strip() for part in address.split(',')]
        if len(parts) < 2:
            return None
        last_part = parts[-1]
        last_part_cleaned = re.sub(r'\b\d{6}\b', '', last_part).strip()
        last_part_cleaned = re.sub(r'\bIndia\b', '', last_part_cleaned, flags=re.IGNORECASE).strip()
        if last_part_cleaned:
            city = parts[-2] if len(parts) >= 2 else None
        else:
            city = parts[-3] if len(parts) >= 3 else None
        if city:
            city = re.sub(r'\b\d{6}\b', '', city).strip()
            city = re.sub(r'\bIndia\b', '', city, flags=re.IGNORECASE).strip()
        return city if city else None

    def extract_state_from_address(self, address):
        """Extract state name from address"""
        if not address:
            return None
        parts = [part.strip() for part in address.split(',')]
        if len(parts) < 2:
            return None
        last_part = parts[-1]
        state = re.sub(r'\b\d{6}\b', '', last_part).strip()
        state = re.sub(r'\bIndia\b', '', state, flags=re.IGNORECASE).strip()
        if not state:
            state = parts[-2] if len(parts) >= 2 else None
            if state:
                state = re.sub(r'\b\d{6}\b', '', state).strip()
                state = re.sub(r'\bIndia\b', '', state, flags=re.IGNORECASE).strip()
        return state if state else None

    def is_relevant_listing(self, listing_text):
        """
        Check if a listing is relevant based on keywords in the FULL listing text
        (includes business name, category, description snippets)
        """
        text_lower = listing_text.lower()

        # Keywords that indicate relevant business
        RELEVANT_KEYWORDS = [
            # Core services
            'ielts', 'pte', 'toefl', 'gre', 'gmat', 'sat', 'oet',
            # Immigration related
            'immigration', 'visa', 'migrate', 'pr consultant', 'permanent resident',
            # Study abroad
            'study abroad', 'overseas education', 'abroad consultant', 'foreign education',
            # Countries
            'canada', 'australia', 'uk study', 'usa study', 'new zealand', 'germany study',
            # Categories
            'immigration consultant', 'visa consultant', 'educational consultant',
            'overseas consultant', 'foreign consultant',
        ]

        # Keywords that indicate NOT relevant (exclude these)
        EXCLUDE_KEYWORDS = [
            'spoken english only', 'personality development', 'soft skill',
            'primary school', 'high school', 'cbse', 'icse',
            'hospital', 'clinic', 'medical college',
            'hotel', 'restaurant', 'cafe',
            'gym', 'fitness', 'salon', 'spa',
            'bank', 'atm', 'finance',
            'real estate', 'property',
        ]

        # Check for relevant keywords
        has_relevant = any(keyword in text_lower for keyword in RELEVANT_KEYWORDS)

        # Check for exclude keywords
        has_exclude = any(keyword in text_lower for keyword in EXCLUDE_KEYWORDS)

        return has_relevant and not has_exclude

    def detect_captcha(self, page):
        """Detect if CAPTCHA is triggered"""
        try:
            if 'sorry' in page.url.lower() and 'google' in page.url.lower():
                return True
            body_text = page.locator('body').inner_text().lower()
            captcha_indicators = [
                'unusual traffic', 'automated requests', 'verify you are human',
                'are you a robot', 'solve this captcha'
            ]
            for indicator in captcha_indicators:
                if indicator in body_text:
                    return True
            return False
        except:
            return False

    def scrape_city(self, query, city, state):
        """Scrape one city"""
        print(f"\n{'='*60}")
        print(f"🔍 Searching: {query}")
        print(f"   🏙️  City: {city}, State: {state}")
        print(f"{'='*60}")

        scroll_count = random.randint(
            self.config['scrolling']['min_scrolls'],
            self.config['scrolling']['max_scrolls']
        )

        headless = self.config.get('headless', True)

        with sync_playwright() as p:
            try:
                # Simple browser setup
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context(
                    viewport={'width': 1200, 'height': 900},
                    locale='en-US',
                )
                page = context.new_page()

                # Step 1: Open Google Maps first
                print(f"  🗺️  Opening Google Maps...")
                page.goto("https://www.google.com/maps", wait_until="load")
                page.wait_for_timeout(random.randint(3000, 4000))

                # Step 2: Wait for search box and type query
                # Format: "PTE IELTS Institute in Bathinda, Punjab"
                search_query = f"{query} in {city}, {state}"
                print(f"  🔍 Searching: {search_query}")

                try:
                    # Wait for search box to be visible (try multiple selectors)
                    search_box = None
                    selectors = [
                        'input#searchboxinput',
                        'input[name="q"]',
                        'input[aria-label="Search Google Maps"]',
                        '#searchbox input'
                    ]

                    for selector in selectors:
                        try:
                            search_box = page.locator(selector).first
                            search_box.wait_for(state="visible", timeout=10000)
                            print(f"  ✓ Found search box")
                            break
                        except:
                            continue

                    if search_box:
                        search_box.click()
                        page.wait_for_timeout(500)
                        page.keyboard.type(search_query, delay=50)
                        page.wait_for_timeout(500)
                        page.keyboard.press('Enter')
                        page.wait_for_timeout(random.randint(4000, 6000))
                    else:
                        print(f"  ⚠️ Could not find search box")
                        browser.close()
                        return {'captcha': False, 'scraped': 0}

                except Exception as e:
                    print(f"  ⚠️ Search error: {e}")
                    browser.close()
                    return {'captcha': False, 'scraped': 0}

                # Check for CAPTCHA
                if self.detect_captcha(page):
                    print("🛑 CAPTCHA detected!")
                    browser.close()
                    return {'captcha': True, 'scraped': 0}

                # Check if results loaded
                try:
                    page.locator('div[role="feed"]').first.wait_for(timeout=5000)
                    print("  ✓ Results panel found")
                except:
                    print("  ⚠️ No results panel")

                # Scroll to load results
                print("📥 Loading results...")
                results_panel = page.locator('div[role="feed"]').first

                for _ in range(scroll_count):
                    try:
                        results_panel.evaluate("el => el.scrollBy({top: 500, behavior: 'smooth'})")
                        page.wait_for_timeout(random.randint(2000, 3500))
                    except:
                        break

                # Get listings
                listings = page.locator('div[role="article"]').all()
                print(f"📊 Found {len(listings)} listings")

                # Collect listing data
                listing_data = []
                filtered_out = 0
                for listing in listings:
                    try:
                        gmb_link = ""
                        business_name = ""
                        try:
                            link_element = listing.locator('a[href*="/maps/place/"]').first
                            gmb_link = link_element.get_attribute('href', timeout=1000)
                            if gmb_link and not gmb_link.startswith('http'):
                                gmb_link = f"https://www.google.com{gmb_link}"
                        except:
                            pass

                        listing_text = listing.inner_text()
                        lines = listing_text.split('\n')
                        if lines:
                            business_name = lines[0]

                        # Filter out irrelevant listings based on keywords
                        if not self.is_relevant_listing(listing_text):
                            filtered_out += 1
                            continue

                        if gmb_link and business_name:
                            listing_data.append({
                                'gmb_link': gmb_link,
                                'business_name': business_name,
                            })
                    except:
                        continue

                print(f"📋 Collected {len(listing_data)} relevant links (filtered out {filtered_out} irrelevant)")

                scraped_count = 0

                # Visit each listing
                for idx, data in enumerate(listing_data):
                    try:
                        business_name = data['business_name']
                        gmb_link = data['gmb_link']

                        print(f"\n[{idx + 1}/{len(listing_data)}] {business_name}")

                        page.goto(gmb_link, wait_until="domcontentloaded")
                        page.wait_for_timeout(random.randint(1500, 2500))

                        # Extract details
                        try:
                            business_name = page.locator('h1.DUwDvf').first.inner_text(timeout=2000)
                        except:
                            pass

                        address = ""
                        try:
                            address_btn = page.locator('button[data-item-id="address"]').first
                            address = address_btn.locator('div.Io6YTe').inner_text(timeout=2000)
                        except:
                            pass

                        phone = None
                        try:
                            phone_btn = page.locator('button[data-item-id^="phone"]').first
                            if phone_btn.count() > 0:
                                phone_text = phone_btn.inner_text(timeout=3000)
                                phone = self.extract_phone(phone_text)
                        except:
                            pass

                        website = ""
                        try:
                            website_btn = page.locator('a[data-item-id="authority"]').first
                            website = website_btn.get_attribute('href', timeout=2000)
                        except:
                            pass

                        if not phone and not website:
                            print(f"  ⚠ Skipping - no phone or website")
                            continue

                        extracted_pincode = self.extract_pincode(address)
                        extracted_city = self.extract_city_from_address(address)
                        extracted_state = self.extract_state_from_address(address)

                        agent_data = {
                            'business_name': business_name,
                            'address': address,
                            'phone': phone if phone else '',
                            'city': extracted_city if extracted_city else city,
                            'state': extracted_state if extracted_state else state,
                            'pincode': extracted_pincode if extracted_pincode else '',
                            'website': website,
                            'email': '',
                            'services': query,
                            'google_place_id': f"gmaps_{int(time.time())}_{idx}",
                            'source_location': f"{query} - {city}, {state}",
                            'latitude': None,
                            'longitude': None,
                            'gmb_link': gmb_link,
                            'status': 'active',
                            'review_count': 0
                        }

                        self.results.append(agent_data)
                        scraped_count += 1
                        print(f"  ✓ Saved")
                        if address:
                            print(f"    📍 {address}")
                        if phone:
                            print(f"    📞 {phone}")

                        page.wait_for_timeout(random.randint(500, 1000))

                    except Exception as e:
                        print(f"  ✗ Error: {str(e)}")
                        continue

                browser.close()
                print(f"\n✓ Scraped {scraped_count} listings from {city}")
                return {'captcha': False, 'scraped': scraped_count}

            except Exception as e:
                print(f"✗ Error: {str(e)}")
                return {'captcha': False, 'scraped': 0, 'error': str(e)}

    def save_results_to_db(self):
        """Save results to database"""
        if not self.results:
            return 0, 0

        try:
            connection = pymysql.connect(**DB_CONFIG)
            cursor = connection.cursor()

            saved_count = 0
            duplicate_count = 0

            for agent in self.results:
                try:
                    # Check for duplicate by phone
                    phone = agent.get('phone')
                    if phone:
                        cursor.execute("SELECT id FROM agents WHERE phone = %s", (phone,))
                        if cursor.fetchone():
                            duplicate_count += 1
                            continue

                    sql = """
                        INSERT INTO agents
                        (business_name, address, phone, city, state, pincode, website, email,
                         services, google_place_id, source_location, latitude, longitude, gmb_link, status, review_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (
                        agent.get('business_name', ''),
                        agent.get('address', ''),
                        agent.get('phone', ''),
                        agent.get('city', ''),
                        agent.get('state', ''),
                        agent.get('pincode', ''),
                        agent.get('website', ''),
                        agent.get('email', ''),
                        agent.get('services', ''),
                        agent.get('google_place_id', ''),
                        agent.get('source_location', ''),
                        agent.get('latitude'),
                        agent.get('longitude'),
                        agent.get('gmb_link', ''),
                        agent.get('status', 'active'),
                        agent.get('review_count', 0)
                    ))
                    saved_count += 1
                except:
                    duplicate_count += 1

            connection.commit()
            cursor.close()
            connection.close()

            print(f"\n💾 Saved {saved_count} new, Skipped {duplicate_count} duplicates")
            return saved_count, duplicate_count

        except Exception as e:
            print(f"✗ Database error: {str(e)}")
            return 0, 0

    def _get_state_key(self, state_name):
        """Map state names to match cities_by_state.json keys"""
        if state_name in self.cities_by_state:
            return state_name

        # Common mappings
        mappings = {
            'Jammu & Kashmir': 'Jammu and Kashmir',
            'Orissa': 'Odisha',
            'Uttaranchal': 'Uttarakhand',
            'Pondicherry': 'Puducherry',
            'Andaman Nicobar': 'Andaman and Nicobar Islands',
            'Dadra & Nagar Haveli': 'Dadra and Nagar Haveli',
        }

        if state_name in mappings and mappings[state_name] in self.cities_by_state:
            return mappings[state_name]

        return None

    def run(self):
        """Main loop"""
        print("\n" + "="*60)
        print("🚀 GOOGLE MAPS SCRAPER - CITY MODE")
        print("="*60)

        queries = self.config['queries']

        # Resume from saved state
        start_state_idx = self.state.get('last_state_index', 0)
        start_city_idx = self.state.get('last_city_index', 0)
        total_scraped = self.state.get('total_scraped', 0)

        if start_state_idx > 0 or start_city_idx > 0:
            print(f"\n🔄 RESUMING from saved state:")
            print(f"   State index: {start_state_idx}")
            print(f"   City index: {start_city_idx}")
            print(f"   Total scraped so far: {total_scraped}")
        else:
            print(f"\n🆕 Starting fresh")

        # Count total cities
        total_cities = sum(
            len(self.cities_by_state.get(self._get_state_key(s) or '', []))
            for s in self.states_to_scrape
        )
        print(f"📊 Total cities to scrape: {total_cities}")

        try:
            for state_idx in range(start_state_idx, len(self.states_to_scrape)):
                state_name = self.states_to_scrape[state_idx]
                state_key = self._get_state_key(state_name)

                if not state_key:
                    print(f"⚠ State not found: {state_name}, skipping...")
                    continue

                cities = self.cities_by_state.get(state_key, [])
                if not cities:
                    continue

                print(f"\n📍 STATE: {state_name} ({len(cities)} cities)")

                city_start = start_city_idx if state_idx == start_state_idx else 0

                for city_idx in range(city_start, len(cities)):
                    city = cities[city_idx]

                    # Pick a random query
                    query = random.choice(queries)

                    # Show current position
                    print(f"\n📊 Progress: State {state_idx + 1}/{len(self.states_to_scrape)}, City {city_idx + 1}/{len(cities)}")

                    # Scrape
                    self.results = []
                    result = self.scrape_city(query, city, state_name)

                    if result.get('captcha'):
                        # Save current position before stopping
                        self.state['last_state_index'] = state_idx
                        self.state['last_city_index'] = city_idx
                        self.save_state()
                        print("🛑 Stopping due to CAPTCHA")
                        return

                    # Save to database
                    self.save_results_to_db()

                    # Update state AFTER successful scrape
                    self.state['last_state_index'] = state_idx
                    self.state['last_city_index'] = city_idx + 1
                    self.state['current_state'] = state_name
                    self.state['current_city'] = city
                    self.state['total_scraped'] = self.state.get('total_scraped', 0) + result.get('scraped', 0)
                    self.save_state()
                    print(f"💾 State saved: {state_name} - {city} ({city_idx + 1}/{len(cities)})")

                    # Delay
                    delay = random.randint(
                        self.config['delays']['min_seconds'],
                        self.config['delays']['max_seconds']
                    )
                    print(f"⏳ Waiting {delay}s...")
                    time.sleep(delay)

                # Reset city index for next state
                self.state['last_city_index'] = 0
                start_city_idx = 0

            print("\n🎉 Completed!")

        except KeyboardInterrupt:
            print("\n⏸ Paused by user")
            self.save_state()


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     GOOGLE MAPS SCRAPER - CITY MODE                      ║
║     1,202 cities across 33 states                        ║
╚══════════════════════════════════════════════════════════╝
    """)

    scraper = BatchScraper()
    scraper.run()


if __name__ == "__main__":
    main()
