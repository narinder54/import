#!/usr/bin/env python3
"""
Google Maps Scraper - City Mode v3
- Zoom-first approach with multi-point zoom for big cities
- Query-first strategy: one query across ALL cities before next query
- 3 combined queries instead of 5
- Uses real Chrome browser (channel="chrome")
- Tracks query+city+zone completion to avoid re-scraping
"""

import sys
import json
import time
import random
import pymysql
from playwright.sync_api import sync_playwright
import re
import os
import urllib.parse

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'immigration_agents_db',
    'charset': 'utf8mb4'
}

# Top cities for --mega mode (dynamic grid will determine zoom points for each)
MEGA_CITIES = {
    # Tier 1 — mega metros
    'Delhi', 'New Delhi', 'Mumbai', 'Bengaluru', 'Chennai', 'Hyderabad',
    'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow', 'Kanpur',
    'Surat', 'Nagpur', 'Thane', 'Navi Mumbai', 'Gurgaon', 'Noida', 'Faridabad',
    # Tier 2 — large cities
    'Indore', 'Bhopal', 'Vadodara', 'Rajkot', 'Coimbatore', 'Madurai',
    'Visakhapatnam', 'Vijayawada', 'Patna', 'Chandigarh', 'Ludhiana',
    'Amritsar', 'Jalandhar', 'Guwahati', 'Ranchi', 'Bhubaneswar',
    'Thiruvananthapuram', 'Kochi', 'Kozhikode', 'Agra', 'Varanasi',
    'Allahabad', 'Meerut', 'Nashik', 'Aurangabad', 'Jodhpur', 'Udaipur',
    'Dehradun', 'Mysore', 'Mangaluru', 'Hubli-Dharwad', 'Tiruchirappalli',
    # Tier 3 — medium cities
    'Patiala', 'Bathinda', 'Bikaner', 'Solapur', 'Salem', 'Tiruppur',
    'Warangal', 'Karimnagar', 'Siliguri', 'Kolhapur', 'Belgaum', 'Belagavi',
    'Rohtak', 'Panipat', 'Sonipat', 'Hisar', 'Karnal', 'Yamunanagar',
    'Hoshiarpur', 'Phagwara', 'Moga',
}

# Approximate visible area (in degrees) per Google Maps zoom level
# Each zoom level halves the visible area
ZOOM_LEVEL_SPAN = {
    8: 1.40, 9: 0.70, 10: 0.35, 11: 0.175, 12: 0.088,
    13: 0.044, 14: 0.022, 15: 0.011, 16: 0.0055, 17: 0.00275,
}

# Scrape zoom level = city auto-zoom + this offset (tighter zoom for scraping)
SCRAPE_ZOOM_EXTRA = 3
# Minimum scrape zoom
MIN_SCRAPE_ZOOM = 15
# Maximum scrape zoom
MAX_SCRAPE_ZOOM = 17


def build_grid_from_bounds(center_lat, center_lng, city_zoom):
    """
    Dynamically build zoom grid from Google Maps auto-zoom level.

    1. City zoom tells us the city's visible span
    2. Scrape zoom = city zoom + SCRAPE_ZOOM_EXTRA (tighter)
    3. We tile the city area with scrape-zoom-sized cells
    """
    # City's visible span from its auto-zoom
    city_span = ZOOM_LEVEL_SPAN.get(city_zoom, 0.044)  # default ~zoom 13

    # Scrape at a tighter zoom level
    scrape_zoom = min(max(city_zoom + SCRAPE_ZOOM_EXTRA, MIN_SCRAPE_ZOOM), MAX_SCRAPE_ZOOM)
    cell_span = ZOOM_LEVEL_SPAN.get(scrape_zoom, 0.011)

    # How many cells we need in each direction from center
    half_span = city_span / 2
    steps = max(1, int(half_span / cell_span))

    # Cap grid based on city zoom level:
    # Wide cities (zoom <=11) = max 5x5 (25 zones)
    # Medium cities (zoom 12-13) = max 3x3 (9 zones)
    # Small cities (zoom >=14) = max 2x2 or 1 center
    if city_zoom <= 11:
        max_steps = 2  # 5x5
    elif city_zoom <= 13:
        max_steps = 1  # 3x3
    else:
        max_steps = 0  # just center
    steps = min(steps, max_steps)

    points = []
    for row in range(-steps, steps + 1):
        for col in range(-steps, steps + 1):
            pt_lat = center_lat + row * cell_span
            pt_lng = center_lng + col * cell_span
            if row == 0 and col == 0:
                name = "center"
            else:
                ns = "n" if row > 0 else ("s" if row < 0 else "")
                ew = "e" if col > 0 else ("w" if col < 0 else "")
                name = f"{ns}{ew}_{abs(row)}{abs(col)}"
            points.append((pt_lat, pt_lng, name))

    return points, scrape_zoom


def detect_city_bounds(page, city, state):
    """
    Search 'City, State' on Google Maps and extract center coords + zoom level
    from the auto-zoomed URL.
    Returns (lat, lng, zoom) or (None, None, None) on failure.
    """
    import re as _re

    search_text = f"{city}, {state}"
    encoded = urllib.parse.quote(search_text)
    url = f"https://www.google.com/maps/search/{encoded}"

    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(random.randint(4000, 6000))

    # Extract coordinates and zoom from the URL
    # URL format: .../@lat,lng,zoomz/...
    current_url = page.url
    match = _re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+),(\d+\.?\d*)z', current_url)
    if match:
        lat = float(match.group(1))
        lng = float(match.group(2))
        zoom = int(float(match.group(3)))
        print(f"  🔍 City bounds detected: center=({lat:.4f}, {lng:.4f}), auto-zoom={zoom}")
        return lat, lng, zoom

    print(f"  ⚠️ Could not detect bounds from URL: {current_url}")
    return None, None, None


class BatchScraper:
    def __init__(self, config_file='batch_config.json', state_file='scraper_state.json',
                 cities_file='cities_by_state.json', coords_file='city_coordinates.json'):
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

        # Load city coordinates
        try:
            self.city_coords = self.load_json(coords_file)
            print(f"✓ Loaded coordinates for {len(self.city_coords)} cities")
        except:
            print("⚠️  Coordinates file not found")
            self.city_coords = {}

        self.states_to_scrape = self.config.get('states_to_scrape', list(self.cities_by_state.keys()))
        self.results = []

        # Track completed searches
        if 'completed_searches' not in self.state:
            self.state['completed_searches'] = []

    def load_json(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {str(e)}")
            return {}

    def save_state(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {str(e)}")

    def is_search_completed(self, query, city, state, zone="center"):
        """Check if this query+city+zone combo was already scraped"""
        key = f"{query}|{city}|{state}|{zone}"
        # Also check old format without zone for backward compat
        old_key = f"{query}|{city}|{state}"
        return key in self.state.get('completed_searches', []) or \
               (zone == "center" and old_key in self.state.get('completed_searches', []))

    def mark_search_completed(self, query, city, state, zone="center"):
        key = f"{query}|{city}|{state}|{zone}"
        if 'completed_searches' not in self.state:
            self.state['completed_searches'] = []
        if key not in self.state['completed_searches']:
            self.state['completed_searches'].append(key)

    def get_city_coordinates(self, city, state):
        key = f"{city}, {state}"
        if key in self.city_coords:
            return self.city_coords[key].get('lat'), self.city_coords[key].get('lng')
        for k, v in self.city_coords.items():
            if city.lower() in k.lower() and state.lower() in k.lower():
                return v.get('lat'), v.get('lng')
        return None, None

    def extract_phone(self, text):
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
        if not address:
            return None
        match = re.search(r'\b\d{6}\b', address)
        return match.group(0) if match else None

    # Union Territories and places where city name = state name
    # For these, the address often has locality/sector instead of city name
    UNION_TERRITORIES = {
        'chandigarh', 'delhi', 'new delhi', 'puducherry', 'pondicherry',
        'goa', 'dadra and nagar haveli', 'andaman and nicobar islands',
        'lakshadweep', 'daman and diu',
    }

    def extract_city_from_address(self, address, search_city=None):
        """
        Extract city from address. If the extracted value looks like a locality
        (sector, block, area, etc.) instead of a real city, fall back to search_city.
        """
        if not address:
            return None

        # Check if the search city name appears directly in the address
        if search_city:
            for part in address.split(','):
                cleaned = part.strip()
                if search_city.lower() in cleaned.lower():
                    return search_city

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

        # If extracted city looks like a locality (sector, block, phase, etc.), reject it
        if city:
            locality_patterns = [
                r'^sector\s', r'^block\s', r'^phase\s', r'^plot\s', r'^pocket\s',
                r'^ward\s', r'^area\s', r'^colony\s', r'^nagar$', r'^vihar$',
                r'^enclave$', r'^extension$', r'^market$', r'^road$', r'^street$',
                r'^lane$', r'^gali\s', r'^mohalla\s', r'^\d+',  # starts with number
            ]
            city_lower = city.lower().strip()
            is_locality = any(re.search(p, city_lower) for p in locality_patterns)
            if is_locality:
                return None  # let the fallback to search_city handle it

        return city if city else None

    def extract_state_from_address(self, address, search_state=None):
        """
        Extract state from address. For Union Territories, use search_state
        since the address format is often ambiguous.
        """
        if not address:
            return None

        # Check if search_state appears in address
        if search_state:
            if search_state.lower() in address.lower():
                return search_state
            # For UTs, the state name IS the city name in the address
            if search_state.lower() in self.UNION_TERRITORIES:
                return search_state

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
        text_lower = listing_text.lower()

        RELEVANT_KEYWORDS = [
            'ielts', 'pte', 'toefl', 'gre', 'gmat', 'sat', 'oet',
            'immigration', 'visa', 'migrate', 'pr consultant', 'permanent resident',
            'study abroad', 'overseas education', 'abroad consultant', 'foreign education',
            'canada', 'australia', 'uk study', 'usa study', 'new zealand', 'germany study',
            'immigration consultant', 'visa consultant', 'educational consultant',
            'overseas consultant', 'foreign consultant',
            'coaching', 'institute', 'academy', 'training',
        ]

        EXCLUDE_KEYWORDS = [
            'spoken english only', 'personality development', 'soft skill',
            'primary school', 'high school', 'cbse', 'icse',
            'hospital', 'clinic', 'medical college',
            'restaurant', 'cafe',
            'gym', 'fitness', 'salon', 'spa',
            'atm',
            'real estate', 'property',
        ]

        has_relevant = any(keyword in text_lower for keyword in RELEVANT_KEYWORDS)
        has_exclude = any(keyword in text_lower for keyword in EXCLUDE_KEYWORDS)
        return has_relevant and not has_exclude

    def detect_captcha(self, page):
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

    def scrape_zone(self, query, city, state, lat, lng, zone_name, browser, context, zoom_level=15):
        """Scrape one zone (one zoom point) within a city"""
        print(f"\n  {'─'*50}")
        print(f"  📍 Zone: {zone_name} ({lat:.4f}, {lng:.4f})")
        print(f"  {'─'*50}")

        scroll_count = random.randint(
            self.config['scrolling']['min_scrolls'],
            self.config['scrolling']['max_scrolls']
        )

        try:
            page = context.new_page()

            # Override geolocation API on every page load to return target city coords
            page.add_init_script("""
                const fakeCoords = {
                    latitude: %s,
                    longitude: %s,
                    accuracy: 50,
                    altitude: null,
                    altitudeAccuracy: null,
                    heading: null,
                    speed: null
                };
                navigator.geolocation.getCurrentPosition = (success, error, options) => {
                    success({ coords: fakeCoords, timestamp: Date.now() });
                };
                navigator.geolocation.watchPosition = (success, error, options) => {
                    success({ coords: fakeCoords, timestamp: Date.now() });
                    return 0;
                };
            """ % (lat, lng))

            # Zoom into specific coordinates using dynamically determined zoom level
            zoom_url = f"https://www.google.com/maps/@{lat},{lng},{zoom_level}z"
            print(f"  🗺️  Zooming to {zoom_level}z...")
            page.goto(zoom_url, wait_until="domcontentloaded")
            page.wait_for_timeout(random.randint(3000, 5000))

            # Search within zoomed area
            try:
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
                        break
                    except:
                        continue

                if search_box:
                    search_box.click()
                    page.wait_for_timeout(300)
                    page.keyboard.press('Control+a')
                    page.wait_for_timeout(200)
                    search_text = query
                    page.keyboard.type(search_text, delay=random.randint(30, 80))
                    page.wait_for_timeout(500)
                    page.keyboard.press('Enter')
                    page.wait_for_timeout(random.randint(4000, 6000))
                    print(f"  ✓ Searched: '{search_text}'")
                else:
                    print(f"  ⚠️ No search box found")
                    page.close()
                    return {'captcha': False, 'scraped': 0}

            except Exception as e:
                print(f"  ⚠️ Search error: {e}")
                page.close()
                return {'captcha': False, 'scraped': 0}

            # Check CAPTCHA
            if self.detect_captcha(page):
                print("  🛑 CAPTCHA detected!")
                page.close()
                return {'captcha': True, 'scraped': 0}

            # Check results panel
            try:
                page.locator('div[role="feed"]').first.wait_for(timeout=8000)
                print("  ✓ Results panel found")
            except:
                print("  ⚠️ No results panel")
                try:
                    single_name = page.locator('h1.DUwDvf').first.inner_text(timeout=3000)
                    print(f"  📌 Single result: {single_name}")
                except:
                    pass
                page.close()
                return {'captcha': False, 'scraped': 0}

            # Scroll to load more results
            results_panel = page.locator('div[role="feed"]').first
            for i in range(scroll_count):
                try:
                    results_panel.evaluate("el => el.scrollBy({top: 500, behavior: 'smooth'})")
                    page.wait_for_timeout(random.randint(1500, 3000))
                    try:
                        end_text = page.locator('span.HlvSq').inner_text(timeout=1000)
                        if end_text:
                            print(f"  ✓ End of results after {i+1} scrolls")
                            break
                    except:
                        pass
                except:
                    break

            # Collect listings
            listings = page.locator('div[role="article"]').all()
            print(f"  📊 Found {len(listings)} listings")

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

            print(f"  📋 {len(listing_data)} relevant ({filtered_out} filtered out)")

            scraped_count = 0

            # Visit each listing detail page
            for idx, data in enumerate(listing_data):
                try:
                    business_name = data['business_name']
                    gmb_link = data['gmb_link']

                    print(f"\n  [{idx + 1}/{len(listing_data)}] {business_name}")

                    page.goto(gmb_link, wait_until="domcontentloaded")
                    page.wait_for_timeout(random.randint(1500, 2500))

                    if self.detect_captcha(page):
                        print("  🛑 CAPTCHA on detail page!")
                        page.close()
                        return {'captcha': True, 'scraped': scraped_count}

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
                        print(f"    ⚠ Skipping - no phone or website")
                        continue

                    # Extract coordinates from URL
                    extracted_lat = None
                    extracted_lng = None
                    try:
                        coord_match = re.search(r'@(-?\d+\.?\d*),(-?\d+\.?\d*)', page.url)
                        if coord_match:
                            extracted_lat = float(coord_match.group(1))
                            extracted_lng = float(coord_match.group(2))
                    except:
                        pass

                    extracted_pincode = self.extract_pincode(address)
                    extracted_city = self.extract_city_from_address(address, search_city=city)
                    extracted_state = self.extract_state_from_address(address, search_state=state)

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
                        'source_location': f"{query} - {city} ({zone_name}), {state}",
                        'latitude': extracted_lat,
                        'longitude': extracted_lng,
                        'gmb_link': gmb_link,
                        'status': 'active',
                        'review_count': 0
                    }

                    self.results.append(agent_data)
                    scraped_count += 1
                    print(f"    ✓ Saved")
                    if address:
                        print(f"      📍 {address}")
                    if phone:
                        print(f"      📞 {phone}")

                    page.wait_for_timeout(random.randint(500, 1000))

                except Exception as e:
                    print(f"    ✗ Error: {str(e)}")
                    continue

            page.close()
            print(f"\n  ✓ Zone {zone_name}: {scraped_count} listings scraped")
            return {'captcha': False, 'scraped': scraped_count}

        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            try:
                page.close()
            except:
                pass
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
                    phone = agent.get('phone')
                    business_name = agent.get('business_name', '')

                    # Primary check: phone number
                    if phone:
                        cursor.execute("SELECT id FROM agents WHERE phone = %s", (phone,))
                        if cursor.fetchone():
                            duplicate_count += 1
                            continue

                    # Fallback check for listings without phone: match by business name
                    if business_name:
                        cursor.execute("SELECT id FROM agents WHERE business_name = %s", (business_name,))
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
        if state_name in self.cities_by_state:
            return state_name
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

    def _build_city_list(self, mode="all"):
        """
        Build flat list of (city, state) tuples.
        mode="all" — all 1,202 cities
        mode="mega" — only the top 50 big cities from MEGA_CITIES dict
        """
        city_list = []
        for state_name in self.states_to_scrape:
            state_key = self._get_state_key(state_name)
            if not state_key:
                continue
            cities = self.cities_by_state.get(state_key, [])
            for city in cities:
                if mode == "mega" and city not in MEGA_CITIES:
                    continue
                city_list.append((city, state_name))
        return city_list

    def run_single_city(self, city, state):
        """Run all queries for a single city (test mode)"""
        print("\n" + "=" * 60)
        print(f"🎯 SINGLE CITY TEST: {city}, {state}")
        print("=" * 60)

        queries = self.config['queries']
        print(f"📋 Queries: {len(queries)}")
        for i, q in enumerate(queries):
            print(f"   {i+1}. {q}")

        headless = self.config.get('headless', True)
        use_chrome = self.config.get('use_chrome', True)

        with sync_playwright() as p:
            try:
                if use_chrome:
                    print("\n🌐 Launching Chrome...")
                    browser = p.chromium.launch(channel="chrome", headless=headless)
                else:
                    browser = p.chromium.launch(headless=headless)

                # Step 1: Detect city bounds by searching city name
                print(f"\n🔍 Detecting bounds for {city}, {state}...")
                detect_ctx = browser.new_context(
                    viewport={'width': 1280, 'height': 900},
                    locale='en-US',
                )
                detect_page = detect_ctx.new_page()
                center_lat, center_lng, city_zoom = detect_city_bounds(detect_page, city, state)
                detect_page.close()
                detect_ctx.close()

                if not center_lat:
                    # Fallback to coordinates file
                    center_lat, center_lng = self.get_city_coordinates(city, state)
                    city_zoom = 13  # default
                    print(f"  📍 Fallback coords: ({center_lat}, {center_lng}), zoom=13")

                # Step 2: Build grid from detected bounds
                zoom_points, scrape_zoom = build_grid_from_bounds(center_lat, center_lng, city_zoom)
                print(f"📌 Grid: {len(zoom_points)} zones at zoom {scrape_zoom} (city auto-zoom was {city_zoom})")
                for zp in zoom_points:
                    print(f"   {zp[2]}: ({zp[0]:.4f}, {zp[1]:.4f})")

                total_scraped = 0

                for q_idx, query in enumerate(queries):
                    print(f"\n{'='*60}")
                    print(f"📌 Query {q_idx+1}/{len(queries)}: {query}")
                    print(f"{'='*60}")

                    # Create context with spoofed geolocation to target city
                    context = browser.new_context(
                        viewport={'width': 1280, 'height': 900},
                        locale='en-US',
                        permissions=['geolocation'],
                        geolocation={'latitude': center_lat, 'longitude': center_lng},
                    )

                    for zp_lat, zp_lng, zone_name in zoom_points:
                        if self.is_search_completed(query, city, state, zone_name):
                            print(f"  ⏭️ {zone_name} already done, skipping")
                            continue

                        self.results = []
                        result = self.scrape_zone(query, city, state, zp_lat, zp_lng, zone_name, browser, context, zoom_level=scrape_zoom)

                        if result.get('captcha'):
                            print("🛑 CAPTCHA! Stopping.")
                            self.save_state()
                            browser.close()
                            return

                        saved, dupes = self.save_results_to_db()
                        total_scraped += result.get('scraped', 0)

                        self.mark_search_completed(query, city, state, zone_name)
                        self.state['total_scraped'] = self.state.get('total_scraped', 0) + result.get('scraped', 0)
                        self.save_state()

                        # Delay between zones
                        if len(zoom_points) > 1:
                            delay = random.randint(3, 8)
                            print(f"  ⏳ Waiting {delay}s before next zone...")
                            time.sleep(delay)

                    context.close()

                    # Delay between queries
                    if q_idx < len(queries) - 1:
                        delay = random.randint(8, 20)
                        print(f"⏳ Waiting {delay}s before next query...")
                        time.sleep(delay)

                browser.close()
                print(f"\n{'='*60}")
                print(f"🎉 DONE: {city}, {state}")
                print(f"   Total new listings: {total_scraped}")
                print(f"{'='*60}")

            except Exception as e:
                print(f"✗ Fatal error: {str(e)}")

    def run(self, mode="all"):
        """
        Main loop - QUERY-FIRST strategy:
        Run query 1 across cities, then query 2, etc.
        mode="all"  — all 1,202 cities
        mode="mega" — only top 50 big cities with multi-point zoom
        """
        mode_label = "MEGA CITIES (Top 50)" if mode == "mega" else "ALL INDIA (1,202 cities)"
        print("\n" + "=" * 60)
        print(f"🚀 GOOGLE MAPS SCRAPER v3 — {mode_label}")
        print("   Query-first + Zoom-first + Multi-point for big cities")
        print("=" * 60)

        queries = self.config['queries']
        city_list = self._build_city_list(mode=mode)

        big_count = sum(1 for c, s in city_list if c in MEGA_CITIES)
        print(f"📋 Queries: {len(queries)}")
        for i, q in enumerate(queries):
            print(f"   {i+1}. {q}")
        print(f"🏙️  Total cities: {len(city_list)} ({big_count} big cities with multi-zoom)")
        print(f"📊 Total scraped so far: {self.state.get('total_scraped', 0)}")

        headless = self.config.get('headless', True)
        use_chrome = self.config.get('use_chrome', True)

        try:
            with sync_playwright() as p:
                if use_chrome:
                    print("\n🌐 Launching Chrome...")
                    browser = p.chromium.launch(channel="chrome", headless=headless)
                else:
                    browser = p.chromium.launch(headless=headless)

                # Cache for detected city bounds (avoid re-detecting per query)
                city_bounds_cache = {}

                # QUERY-FIRST: iterate queries in outer loop, cities in inner loop
                for q_idx, query in enumerate(queries):
                    print(f"\n{'='*60}")
                    print(f"🔎 PASS {q_idx+1}/{len(queries)}: {query}")
                    print(f"   Across all {len(city_list)} cities")
                    print(f"{'='*60}")

                    for city_idx, (city, state) in enumerate(city_list):

                        # Detect city bounds (once per city, cached)
                        cache_key = f"{city}|{state}"
                        if cache_key not in city_bounds_cache:
                            print(f"\n🔍 Detecting bounds for {city}, {state}...")
                            detect_ctx = browser.new_context(
                                viewport={'width': 1280, 'height': 900},
                                locale='en-US',
                            )
                            detect_page = detect_ctx.new_page()
                            c_lat, c_lng, c_zoom = detect_city_bounds(detect_page, city, state)
                            detect_page.close()
                            detect_ctx.close()

                            if not c_lat:
                                c_lat, c_lng = self.get_city_coordinates(city, state)
                                c_zoom = 13
                                print(f"  📍 Fallback coords: ({c_lat}, {c_lng}), zoom=13")

                            if c_lat and c_lng:
                                points, s_zoom = build_grid_from_bounds(c_lat, c_lng, c_zoom)
                                city_bounds_cache[cache_key] = (c_lat, c_lng, points, s_zoom)
                                print(f"  📌 Grid: {len(points)} zones at zoom {s_zoom}")
                            else:
                                print(f"  ⚠️ No coordinates for {city}, {state} — skipping")
                                city_bounds_cache[cache_key] = None
                                continue

                            # Small delay after detection
                            time.sleep(random.randint(2, 4))

                        cached = city_bounds_cache.get(cache_key)
                        if not cached:
                            continue
                        center_lat, center_lng, zoom_points, scrape_zoom = cached

                        # Check if ALL zones for this city+query are done
                        all_done = all(
                            self.is_search_completed(query, city, state, zn)
                            for _, _, zn in zoom_points
                        )
                        if all_done:
                            continue

                        print(f"\n📊 [{city_idx+1}/{len(city_list)}] {city}, {state} ({len(zoom_points)} zones, zoom {scrape_zoom})")

                        # Create context with spoofed geolocation to target city
                        context = browser.new_context(
                            viewport={'width': 1280, 'height': 900},
                            locale='en-US',
                            permissions=['geolocation'],
                            geolocation={'latitude': center_lat, 'longitude': center_lng},
                        )

                        for zp_lat, zp_lng, zone_name in zoom_points:
                            if self.is_search_completed(query, city, state, zone_name):
                                print(f"  ⏭️ {zone_name} done")
                                continue

                            self.results = []
                            result = self.scrape_zone(query, city, state, zp_lat, zp_lng, zone_name, browser, context, zoom_level=scrape_zoom)

                            if result.get('captcha'):
                                self.save_state()
                                print("🛑 CAPTCHA! Stopping. Resume later to continue.")
                                browser.close()
                                return

                            self.save_results_to_db()
                            self.mark_search_completed(query, city, state, zone_name)
                            self.state['total_scraped'] = self.state.get('total_scraped', 0) + result.get('scraped', 0)
                            self.state['current_query'] = query
                            self.state['current_city'] = city
                            self.state['current_state'] = state
                            self.save_state()

                            # Delay between zones
                            if len(zoom_points) > 1:
                                delay = random.randint(3, 8)
                                time.sleep(delay)

                        # Close context after each city
                        context.close()

                        # Delay between cities
                        delay = random.randint(
                            self.config['delays']['min_seconds'],
                            self.config['delays']['max_seconds']
                        )
                        print(f"⏳ {delay}s before next city...")
                        time.sleep(delay)

                    print(f"\n✅ PASS {q_idx+1} COMPLETE: '{query}' done for all cities")

                browser.close()
                print("\n🎉 ALL PASSES COMPLETE!")

        except KeyboardInterrupt:
            print("\n⏸ Paused by user. Run again to resume.")
            self.save_state()


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     GOOGLE MAPS SCRAPER v3                               ║
║     Query-first + Multi-point zoom for big cities        ║
║                                                          ║
║  Usage:                                                  ║
║    python3 batch_scraper.py                  (all India)  ║
║    python3 batch_scraper.py --mega       (top 50 cities)  ║
║    python3 batch_scraper.py "City" "State" (single city)  ║
╚══════════════════════════════════════════════════════════╝
    """)

    if "--mega" in sys.argv:
        print("🏙️  MEGA MODE: Scraping top 50 cities with multi-point zoom")
        scraper = BatchScraper()
        scraper.run(mode="mega")
    elif len(sys.argv) >= 3 and not sys.argv[1].startswith("--"):
        city = sys.argv[1]
        state = sys.argv[2]
        print(f"🎯 Single city mode: {city}, {state}")
        scraper = BatchScraper()
        scraper.run_single_city(city, state)
    else:
        scraper = BatchScraper()
        scraper.run(mode="all")


if __name__ == "__main__":
    main()
