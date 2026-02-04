#!/usr/bin/env python3
"""
Update Business Status from GMB Links
Scans through all database records and checks if businesses are closed
by visiting their Google Maps Business links.
Also extracts the number of reviews/ratings and phone numbers for each business.
Supports resuming from last checked record.
"""

import pymysql
import time
import random
import re
import sys
import json
import os
from playwright.sync_api import sync_playwright

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'immigration_agents_db',
    'unix_socket': '/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock'
}

# State file for resuming
STATE_FILE = 'gmb_checker_state.json'

class StatusUpdater:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.state_file = STATE_FILE
        self.state = {
            'last_checked_id': 0,
            'last_checked_index': 0,
            'status': 'idle'
        }
        self.stats = {
            'total': 0,
            'checked': 0,
            'updated_temp_closed': 0,
            'updated_perm_closed': 0,
            'still_active': 0,
            'no_gmb_link': 0,
            'errors': 0,
            'reviews_updated': 0,
            'phones_updated': 0
        }

        # Load existing state if available
        self.load_state()

    def load_state(self):
        """Load saved state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                print(f"📂 Loaded saved state: Last checked ID = {self.state.get('last_checked_id', 0)}")
        except Exception as e:
            print(f"⚠️ Could not load state: {e}")

    def save_state(self, agent_id, index):
        """Save current state to file"""
        try:
            self.state['last_checked_id'] = agent_id
            self.state['last_checked_index'] = index
            self.state['status'] = 'running'
            self.state['stats'] = self.stats
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save state: {e}")

    def clear_state(self):
        """Clear saved state (when completed)"""
        try:
            self.state = {
                'last_checked_id': 0,
                'last_checked_index': 0,
                'status': 'completed'
            }
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            print("✅ State cleared - ready for fresh start")
        except Exception as e:
            print(f"⚠️ Could not clear state: {e}")

    def connect_db(self):
        """Connect to database"""
        try:
            self.connection = pymysql.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            print("✅ Connected to database")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

    def get_all_agents(self, resume_from_id=0):
        """Get all agents with GMB links that are currently active"""
        query = """
            SELECT id, business_name, city, state, gmb_link, status, phone
            FROM agents
            WHERE gmb_link IS NOT NULL
              AND gmb_link != ''
              AND status = 'active'
              AND id > %s
            ORDER BY id ASC
        """
        self.cursor.execute(query, (resume_from_id,))
        return self.cursor.fetchall()

    def extract_phone(self, text):
        """Extract phone number from text"""
        if not text:
            return None

        # Clean the text first
        text = text.replace('\n', ' ').replace('\t', ' ')

        patterns = [
            r'\+91[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d[\s\-\.]*\d',  # +91 with any separators
            r'\+91[\s-]?\d{10}',  # +91 followed by 10 digits
            r'\+91[\s-]?\d{5}[\s-]?\d{5}',  # +91 XXXXX XXXXX
            r'0\d{2,4}[\s\-\.]*\d{6,8}',  # STD code format
            r'\(\d{3,5}\)[\s-]?\d{6,8}',  # (0XXX) XXXXXXX format
            r'\d{10}',  # Plain 10 digits
            r'\d{5}[\s-]\d{5}',  # XXXXX XXXXX format
            r'\d{4}[\s-]\d{3}[\s-]\d{3}',  # XXXX XXX XXX format
            r'\d{3}[\s-]\d{3}[\s-]\d{4}',  # XXX XXX XXXX format
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                # Clean up the matched phone number
                phone = match.group(0).strip()
                # Remove extra spaces/dashes but keep the number readable
                phone = re.sub(r'[\s\-\.]+', ' ', phone).strip()
                return phone
        return None

    def update_agent(self, agent_id, new_status=None, review_count=None, phone=None):
        """Update agent status, review count, and/or phone in database"""
        try:
            updates = []
            values = []

            if new_status:
                updates.append("status = %s")
                values.append(new_status)
            if review_count is not None:
                updates.append("review_count = %s")
                values.append(review_count)
            if phone:
                updates.append("phone = %s")
                values.append(phone)

            if updates:
                values.append(agent_id)
                query = f"UPDATE agents SET {', '.join(updates)} WHERE id = %s"
                self.cursor.execute(query, tuple(values))
                self.connection.commit()
            return True
        except Exception as e:
            print(f"  ❌ Error updating: {e}")
            return False

    def check_business_status(self, page, gmb_link):
        """Check if business is closed, get review count and phone by visiting GMB link"""
        try:
            # Navigate to GMB link
            page.goto(gmb_link, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(random.randint(2000, 3000))

            # Get page content
            page_text = page.content().lower()
            page_html = page.content()

            # Determine status - check temporarily closed FIRST (more specific)
            status = 'active'
            if 'temporarily closed' in page_text:
                status = 'temporarily closed'
            elif 'permanently closed' in page_text:
                status = 'permanently closed'

            # Extract review count
            review_count = 0
            try:
                review_patterns = [
                    r'(\d{1,3}(?:,\d{3})*)\s*reviews?',  # "123 reviews" or "1,234 reviews"
                    r'\((\d{1,3}(?:,\d{3})*)\)',  # "(123)" near rating
                    r'aria-label="[^"]*(\d{1,3}(?:,\d{3})*)\s*reviews?',  # aria-label with reviews
                ]

                for pattern in review_patterns:
                    matches = re.findall(pattern, page_html, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            num_str = match.replace(',', '')
                            if num_str.isdigit():
                                review_count = int(num_str)
                                break
                    if review_count > 0:
                        break
            except:
                pass

            # Extract phone number - try multiple methods
            phone = None
            try:
                # Method 1: Standard phone button
                phone_btn = page.locator('button[data-item-id^="phone"]').first
                if phone_btn.count() > 0:
                    phone_text = phone_btn.inner_text(timeout=3000)
                    phone = self.extract_phone(phone_text)

                # Method 2: Try aria-label containing phone
                if not phone:
                    phone_link = page.locator('a[aria-label*="Phone"], a[data-tooltip*="phone"], button[aria-label*="Phone"]').first
                    if phone_link.count() > 0:
                        phone_text = phone_link.get_attribute('aria-label', timeout=3000) or phone_link.inner_text(timeout=3000)
                        phone = self.extract_phone(phone_text)

                # Method 3: Look for phone section
                if not phone:
                    phone_section = page.locator('[data-item-id*="phone"], [aria-label*="hone"]').first
                    if phone_section.count() > 0:
                        phone_text = phone_section.inner_text(timeout=3000)
                        phone = self.extract_phone(phone_text)

                # Method 4: Search in entire detail panel
                if not phone:
                    detail_panel = page.locator('div[role="main"]').first
                    if detail_panel.count() > 0:
                        panel_text = detail_panel.inner_text(timeout=3000)
                        phone = self.extract_phone(panel_text)
            except:
                pass

            return {'status': status, 'review_count': review_count, 'phone': phone}

        except Exception as e:
            print(f"  ⚠️ Error checking page: {str(e)[:50]}")
            return None

    def run(self, start_from=0, batch_size=None, resume=False):
        """Main function to check all agents"""
        print("\n" + "="*70)
        print("🔍 GMB STATUS CHECKER - Scanning Database for Closed Businesses")
        print("="*70 + "\n")

        # Connect to database
        if not self.connect_db():
            return

        # Determine starting point
        resume_from_id = 0
        if resume and self.state.get('last_checked_id', 0) > 0:
            resume_from_id = self.state['last_checked_id']
            print(f"🔄 RESUMING from last checked ID: {resume_from_id}")
            # Load previous stats if available
            if 'stats' in self.state:
                self.stats = self.state['stats']
                print(f"   📊 Previous progress: {self.stats['checked']} checked")

        # Get all agents (starting from resume point if applicable)
        agents = self.get_all_agents(resume_from_id)
        self.stats['total'] = len(agents) + self.stats.get('checked', 0)

        if not agents:
            if resume_from_id > 0:
                print("✅ All records already checked! Use --reset to start fresh.")
            else:
                print("No active agents with GMB links found.")
            return

        print(f"📊 Found {len(agents)} agents remaining to check")

        if start_from > 0 and not resume:
            agents = agents[start_from:]
            print(f"⏩ Starting from record #{start_from + 1}")

        if batch_size:
            agents = agents[:batch_size]
            print(f"📦 Processing batch of {batch_size} records")

        print("\n" + "-"*70)

        # Start browser
        with sync_playwright() as p:
            print("\n🌐 Launching browser...")

            browser = p.firefox.launch(
                headless=False,  # Show browser window
                args=['--no-sandbox']
            )

            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

            page = context.new_page()

            try:
                for idx, agent in enumerate(agents):
                    agent_id = agent['id']
                    business_name = agent['business_name']
                    city = agent['city']
                    state = agent['state']
                    gmb_link = agent['gmb_link']
                    current_status = agent['status']
                    current_phone = agent.get('phone', '') or ''

                    print(f"\n[{idx + 1}/{len(agents)}] Checking: {business_name[:50]}")
                    print(f"  📍 {city}, {state}")

                    if not gmb_link:
                        print(f"  ⚠️ No GMB link - skipping")
                        self.stats['no_gmb_link'] += 1
                        continue

                    # Check business status, review count and phone
                    result = self.check_business_status(page, gmb_link)

                    if result is None:
                        self.stats['errors'] += 1
                        continue

                    self.stats['checked'] += 1

                    new_status = result['status']
                    review_count = result['review_count']
                    new_phone = result.get('phone')

                    # Check if phone needs updating (only if current phone is empty and we found a new one)
                    phone_to_update = None
                    if new_phone and not current_phone.strip():
                        phone_to_update = new_phone
                        self.stats['phones_updated'] += 1

                    # Determine what to update
                    if new_status == 'temporarily closed':
                        print(f"  ⏸️  TEMPORARILY CLOSED - Updating database")
                        if self.update_agent(agent_id, 'temporarily closed', review_count, phone_to_update):
                            self.stats['updated_temp_closed'] += 1
                            if review_count > 0:
                                self.stats['reviews_updated'] += 1
                                print(f"  ⭐ Reviews: {review_count}")
                            if phone_to_update:
                                print(f"  📞 Phone added: {phone_to_update}")
                    elif new_status == 'permanently closed':
                        print(f"  ⛔ PERMANENTLY CLOSED - Updating database")
                        if self.update_agent(agent_id, 'permanently closed', review_count, phone_to_update):
                            self.stats['updated_perm_closed'] += 1
                            if review_count > 0:
                                self.stats['reviews_updated'] += 1
                                print(f"  ⭐ Reviews: {review_count}")
                            if phone_to_update:
                                print(f"  📞 Phone added: {phone_to_update}")
                    else:
                        # Still active - update review count and/or phone if found
                        status_msg = "  ✅ Active"
                        if review_count > 0 or phone_to_update:
                            self.update_agent(agent_id, review_count=review_count if review_count > 0 else None, phone=phone_to_update)
                            if review_count > 0:
                                self.stats['reviews_updated'] += 1
                                status_msg += f" | ⭐ Reviews: {review_count}"
                            if phone_to_update:
                                status_msg += f" | 📞 Phone added: {phone_to_update}"
                            print(status_msg)
                        else:
                            print(f"  ✅ Still active")
                        self.stats['still_active'] += 1

                    # Save state after each record
                    self.save_state(agent_id, idx)

                    # Random delay to avoid detection
                    delay = random.uniform(1.5, 3.0)
                    time.sleep(delay)

                    # Save progress periodically
                    if (idx + 1) % 50 == 0:
                        self.print_progress()

                # Completed successfully - clear state
                self.clear_state()

            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted by user")
                print(f"💾 Progress saved. Resume with: python3 update_status_from_gmb.py --resume")
            finally:
                browser.close()

        # Final summary
        self.print_summary()

        # Close database connection
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def print_progress(self):
        """Print current progress"""
        print("\n" + "-"*40)
        print(f"📊 Progress: {self.stats['checked']}/{self.stats['total']} checked")
        print(f"   ✅ Active: {self.stats['still_active']}")
        print(f"   ⏸️  Temp Closed: {self.stats['updated_temp_closed']}")
        print(f"   ⛔ Perm Closed: {self.stats['updated_perm_closed']}")
        print(f"   ⭐ Reviews Updated: {self.stats['reviews_updated']}")
        print(f"   📞 Phones Updated: {self.stats['phones_updated']}")
        print("-"*40 + "\n")

    def print_summary(self):
        """Print final summary"""
        print("\n" + "="*70)
        print("📊 FINAL SUMMARY")
        print("="*70)
        print(f"  📋 Total records in database: {self.stats['total']}")
        print(f"  🔍 Records checked: {self.stats['checked']}")
        print(f"  ✅ Still active: {self.stats['still_active']}")
        print(f"  ⏸️  Updated to 'temporarily closed': {self.stats['updated_temp_closed']}")
        print(f"  ⛔ Updated to 'permanently closed': {self.stats['updated_perm_closed']}")
        print(f"  ⭐ Review counts updated: {self.stats['reviews_updated']}")
        print(f"  📞 Phone numbers added: {self.stats['phones_updated']}")
        print(f"  ⚠️  No GMB link: {self.stats['no_gmb_link']}")
        print(f"  ❌ Errors: {self.stats['errors']}")
        print("="*70 + "\n")

        total_updated = self.stats['updated_temp_closed'] + self.stats['updated_perm_closed']
        if total_updated > 0:
            print(f"✅ Updated {total_updated} business statuses in database!")
        else:
            print("✅ All checked businesses are still active!")

        if self.stats['reviews_updated'] > 0:
            print(f"⭐ Updated review counts for {self.stats['reviews_updated']} businesses!")

        if self.stats['phones_updated'] > 0:
            print(f"📞 Added phone numbers for {self.stats['phones_updated']} businesses!")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Check and update business status from GMB links')
    parser.add_argument('--start', type=int, default=0, help='Start from record number (0-indexed)')
    parser.add_argument('--batch', type=int, default=None, help='Number of records to process')
    parser.add_argument('--test', action='store_true', help='Test mode - check first 10 records only')
    parser.add_argument('--resume', action='store_true', help='Resume from last saved position')
    parser.add_argument('--reset', action='store_true', help='Reset saved state and start fresh')

    args = parser.parse_args()

    updater = StatusUpdater()

    # Handle reset
    if args.reset:
        updater.clear_state()
        print("🔄 State reset. Starting fresh...")

    if args.test:
        print("🧪 TEST MODE - Checking first 10 records only")
        updater.run(start_from=0, batch_size=10, resume=False)
    elif args.resume:
        print("🔄 RESUME MODE - Continuing from last saved position")
        updater.run(batch_size=args.batch, resume=True)
    else:
        updater.run(start_from=args.start, batch_size=args.batch, resume=False)


if __name__ == "__main__":
    main()
