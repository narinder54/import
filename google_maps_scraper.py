#!/usr/bin/env python3
"""
Google Maps Scraper for Immigration Agents
Uses Playwright for browser automation
"""

import sys
import json
import time
import re
import pymysql
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'immigration_agents_db',
    'charset': 'utf8mb4'
}

class GoogleMapsScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.results = []

    def check_duplicate(self, cursor, phone, business_name, city):
        """Check if entry already exists in database"""
        if phone:
            cursor.execute("SELECT id FROM agents WHERE phone = %s", (phone,))
            if cursor.fetchone():
                return True

        if business_name and city:
            cursor.execute("SELECT id FROM agents WHERE business_name = %s AND city = %s",
                          (business_name, city))
            if cursor.fetchone():
                return True

        return False

    def insert_agent(self, cursor, data):
        """Insert agent data into database"""
        try:
            # Check for duplicate
            if self.check_duplicate(cursor, data.get('phone'), data.get('business_name'), data.get('city')):
                return {'success': False, 'message': 'Duplicate - already exists'}

            sql = """
                INSERT INTO agents
                (business_name, address, phone, city, state, pincode, website, email,
                 services, google_place_id, source_location, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(sql, (
                data.get('business_name', ''),
                data.get('address', ''),
                data.get('phone', ''),
                data.get('city', ''),
                data.get('state', ''),
                data.get('pincode', ''),
                data.get('website', ''),
                data.get('email', ''),
                data.get('services', ''),
                data.get('google_place_id', ''),
                data.get('source_location', ''),
                data.get('latitude'),
                data.get('longitude')
            ))

            return {'success': True, 'id': cursor.lastrowid}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def extract_phone(self, text):
        """Extract phone number from text"""
        if not text:
            return None
        # Indian phone number patterns
        patterns = [
            r'\+91[\s-]?\d{10}',
            r'0\d{2,4}[\s-]?\d{6,8}',
            r'\d{10}',
            r'\d{5}[\s-]\d{5}'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return None

    def extract_pincode(self, address):
        """Extract PIN code from address"""
        if not address:
            return None
        match = re.search(r'\b\d{6}\b', address)
        return match.group(0) if match else None

    def detect_services_from_name(self, business_name, google_category=None, search_query=None):
        """
        Intelligently detect services from business name and category
        Returns: comma-separated string with primary service first
        """
        business_lower = business_name.lower()
        detected_services = []
        service_positions = {}

        # Service keywords with priority weights
        service_keywords = {
            'immigration': ['immigration', 'immigrate', 'visa consultant', 'pr consultant', 'migrate'],
            'visa': ['visa', 'passport'],
            'ielts': ['ielts', 'british council'],
            'pte': ['pte', 'pearson'],
            'toefl': ['toefl'],
            'study abroad': ['study abroad', 'overseas education', 'abroad', 'overseas'],
            'coaching': ['coaching', 'academy', 'institute', 'training center', 'classes']
        }

        # Priority 1: Google Maps category (most reliable)
        if google_category:
            category_lower = google_category.lower()
            if 'immigra' in category_lower or 'visa' in category_lower:
                detected_services.insert(0, 'immigration consultant')
            elif 'ielts' in category_lower or 'language' in category_lower:
                detected_services.insert(0, 'IELTS coaching')
            elif 'pte' in category_lower:
                detected_services.insert(0, 'PTE coaching')
            elif 'education' in category_lower or 'study' in category_lower:
                detected_services.insert(0, 'study abroad consultant')

        # Priority 2: Analyze business name (keyword position matters)
        for service, keywords in service_keywords.items():
            for keyword in keywords:
                if keyword in business_lower:
                    position = business_lower.find(keyword)
                    # Store earliest position if multiple keywords match same service
                    if service not in service_positions or position < service_positions[service]:
                        service_positions[service] = position

        # Sort services by position in name (earlier = more important)
        sorted_services = sorted(service_positions.items(), key=lambda x: x[1])

        # Map to standardized service names
        service_mapping = {
            'immigration': 'immigration consultant',
            'visa': 'visa consultant',
            'ielts': 'IELTS coaching',
            'pte': 'PTE coaching',
            'toefl': 'TOEFL coaching',
            'study abroad': 'study abroad consultant',
            'coaching': None  # Generic, don't add unless specific
        }

        # Build service list based on name analysis
        for service, position in sorted_services:
            mapped_service = service_mapping.get(service)
            if mapped_service and mapped_service not in detected_services:
                detected_services.append(mapped_service)

        # Priority 3: Add search query if not already detected
        if search_query and search_query not in detected_services:
            detected_services.append(search_query)

        # If nothing detected, use search query as fallback
        if not detected_services and search_query:
            detected_services.append(search_query)

        # Return comma-separated with primary first
        return ', '.join(detected_services) if detected_services else ''

    def extract_state_from_address(self, address):
        """Extract state name from address"""
        if not address:
            return ''

        address_lower = address.lower()

        # State name patterns and abbreviations
        state_mappings = {
            'maharashtra': 'Maharashtra', 'mh': 'Maharashtra',
            'karnataka': 'Karnataka', 'ka': 'Karnataka',
            'tamil nadu': 'Tamil Nadu', 'tamilnadu': 'Tamil Nadu', 'tn': 'Tamil Nadu',
            'telangana': 'Telangana', 'tg': 'Telangana',
            'andhra pradesh': 'Andhra Pradesh', 'ap': 'Andhra Pradesh',
            'gujarat': 'Gujarat', 'gj': 'Gujarat',
            'rajasthan': 'Rajasthan', 'rj': 'Rajasthan',
            'uttar pradesh': 'Uttar Pradesh', 'up': 'Uttar Pradesh',
            'madhya pradesh': 'Madhya Pradesh', 'mp': 'Madhya Pradesh',
            'punjab': 'Punjab', 'pb': 'Punjab',
            'haryana': 'Haryana', 'hr': 'Haryana',
            'west bengal': 'West Bengal', 'wb': 'West Bengal',
            'kerala': 'Kerala', 'kl': 'Kerala',
            'odisha': 'Odisha', 'orissa': 'Odisha', 'or': 'Odisha',
            'jharkhand': 'Jharkhand', 'jh': 'Jharkhand',
            'assam': 'Assam', 'as': 'Assam',
            'bihar': 'Bihar', 'br': 'Bihar',
            'chhattisgarh': 'Chhattisgarh', 'cg': 'Chhattisgarh',
            'goa': 'Goa', 'ga': 'Goa',
            'himachal pradesh': 'Himachal Pradesh', 'hp': 'Himachal Pradesh',
            'jammu and kashmir': 'Jammu and Kashmir', 'jk': 'Jammu and Kashmir',
            'delhi': 'Delhi', 'new delhi': 'Delhi', 'dl': 'Delhi',
            'chandigarh': 'Chandigarh', 'ch': 'Chandigarh',
            'puducherry': 'Puducherry', 'pondicherry': 'Puducherry', 'py': 'Puducherry',
            'uttarakhand': 'Uttarakhand', 'uk': 'Uttarakhand',
        }

        for key, state_name in state_mappings.items():
            if key in address_lower:
                return state_name

        return ''

    def scrape_google_maps(self, query, location, max_results=20):
        """
        Scrape Google Maps for business listings

        Args:
            query: Search query (e.g., "immigration consultant", "IELTS coaching")
            location: Location to search (e.g., "Delhi", "Mumbai")
            max_results: Maximum number of results to scrape
        """
        search_term = f"{query} {location}"
        print(f"Searching for: {search_term}")

        with sync_playwright() as p:
            try:
                # Use Firefox instead of Chromium (better macOS compatibility, no code signing issues)
                # For macOS: set environment variable to disable codesign check
                import os as os_module
                os_module.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

                browser = p.firefox.launch(
                    headless=self.headless,
                    firefox_user_prefs={
                        'dom.webdriver.enabled': False,
                        'useAutomationExtension': False
                    },
                    env={
                        'OBJC_DISABLE_INITIALIZE_FORK_SAFETY': 'YES'
                    }
                )
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    ignore_https_errors=True
                )
                page = context.new_page()

                # Go to Google Maps
                print("Opening Google Maps...")
                page.goto("https://www.google.com/maps", wait_until="domcontentloaded")
                page.wait_for_timeout(5000)

                # Take screenshot for debugging
                page.screenshot(path="debug_screenshot.png")
                print("Screenshot saved to debug_screenshot.png")

                # Try direct URL navigation with search term instead
                print(f"Navigating to search: {search_term}")
                import urllib.parse
                encoded_query = urllib.parse.quote(search_term)
                search_url = f"https://www.google.com/maps/search/{encoded_query}"
                page.goto(search_url, wait_until="domcontentloaded")
                print("Search page loaded")

                # Wait for results to load
                page.wait_for_timeout(5000)

                # Scroll to load more results
                print("Loading results...")
                results_panel = page.locator('div[role="feed"]').first

                for i in range(3):  # Scroll 3 times to load more results
                    try:
                        results_panel.evaluate("el => el.scrollTo(0, el.scrollHeight)")
                        page.wait_for_timeout(2000)
                    except:
                        pass

                # Get all business listings
                listings = page.locator('div[role="article"]').all()
                print(f"Found {len(listings)} listings")

                scraped_count = 0

                for idx, listing in enumerate(listings[:max_results]):
                    try:
                        print(f"\nProcessing listing {idx + 1}/{min(len(listings), max_results)}...")

                        # Click on listing to get details
                        listing.click()
                        page.wait_for_timeout(3000)

                        # Extract business name
                        try:
                            business_name = page.locator('h1.DUwDvf').first.inner_text()
                        except:
                            business_name = "Unknown"

                        print(f"Business: {business_name}")

                        # Extract category (usually appears after business name)
                        google_category = None
                        try:
                            category_element = page.locator('button[jsaction*="category"]').first
                            google_category = category_element.inner_text()
                        except:
                            try:
                                # Alternative: category might be in a span with class
                                google_category = page.locator('.DkEaL').first.inner_text()
                            except:
                                pass

                        if google_category:
                            print(f"Category: {google_category}")

                        # Extract address
                        try:
                            address_btn = page.locator('button[data-item-id="address"]').first
                            address = address_btn.locator('div.Io6YTe').inner_text()
                        except:
                            address = ""

                        # Extract phone
                        phone = ""
                        try:
                            phone_btn = page.locator('button[data-item-id^="phone"]').first
                            phone_text = phone_btn.inner_text()
                            phone = self.extract_phone(phone_text)
                        except:
                            pass

                        # Extract website
                        website = ""
                        try:
                            website_btn = page.locator('a[data-item-id="authority"]').first
                            website = website_btn.get_attribute('href')
                        except:
                            pass

                        # Extract PIN code from address
                        pincode = self.extract_pincode(address)

                        # Extract state from address
                        state = self.extract_state_from_address(address)

                        # Detect services intelligently from category, name, and query
                        services = self.detect_services_from_name(business_name, google_category, query)

                        # Create agent data
                        agent_data = {
                            'business_name': business_name,
                            'address': address,
                            'phone': phone,
                            'city': location,
                            'state': state,
                            'pincode': pincode,
                            'website': website,
                            'email': '',
                            'services': services,
                            'google_place_id': f"gmaps_{int(time.time())}_{idx}",
                            'source_location': f"{query} - {location}",
                            'latitude': None,
                            'longitude': None
                        }

                        self.results.append(agent_data)
                        scraped_count += 1

                        print(f"✓ Scraped: {business_name}")
                        print(f"  Services: {services}")

                        # Random delay to avoid detection
                        page.wait_for_timeout(1000 + (idx % 3) * 500)

                    except Exception as e:
                        print(f"Error processing listing {idx + 1}: {str(e)}")
                        continue

                browser.close()
                print(f"\n✓ Successfully scraped {scraped_count} listings")
                return scraped_count

            except Exception as e:
                print(f"Error during scraping: {str(e)}")
                return 0

    def save_to_database(self):
        """Save scraped results to database"""
        if not self.results:
            print("No results to save")
            return 0

        try:
            connection = pymysql.connect(**DB_CONFIG)
            cursor = connection.cursor()

            saved_count = 0
            duplicate_count = 0

            for agent in self.results:
                result = self.insert_agent(cursor, agent)
                if result['success']:
                    saved_count += 1
                    print(f"✓ Saved: {agent['business_name']}")
                else:
                    duplicate_count += 1
                    print(f"⊗ Skipped (duplicate): {agent['business_name']}")

            connection.commit()
            cursor.close()
            connection.close()

            print(f"\n✓ Saved {saved_count} new agents to database")
            print(f"⊗ Skipped {duplicate_count} duplicates")

            return saved_count

        except Exception as e:
            print(f"Database error: {str(e)}")
            return 0

    def save_to_json(self, filename):
        """Save results to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved results to {filename}")


def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Usage: python google_maps_scraper.py <query> <location> [max_results] [headless]")
        print("Example: python google_maps_scraper.py 'immigration consultant' 'Delhi' 20 true")
        sys.exit(1)

    query = sys.argv[1]
    location = sys.argv[2]
    max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    headless = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True

    scraper = GoogleMapsScraper(headless=headless)

    # Scrape Google Maps
    count = scraper.scrape_google_maps(query, location, max_results)

    if count > 0:
        # Save to database
        saved = scraper.save_to_database()

        # Also save to JSON for backup
        json_filename = f"scraped_{query.replace(' ', '_')}_{location}_{int(time.time())}.json"
        scraper.save_to_json(json_filename)

        # Return results as JSON
        result = {
            'success': True,
            'scraped': count,
            'saved': saved,
            'duplicates': count - saved,
            'message': f"Successfully scraped {count} listings, saved {saved} new agents"
        }
    else:
        result = {
            'success': False,
            'scraped': 0,
            'saved': 0,
            'message': 'No results found or error occurred'
        }

    print("\n" + "="*50)
    print(json.dumps(result, indent=2))
    print("="*50)


if __name__ == "__main__":
    main()
