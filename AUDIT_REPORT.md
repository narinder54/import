# Google Maps Scraper - Project Audit Report
**Date:** April 7, 2026
**Project:** Immigration Business Scraper (India)

---

## 1. Current State Summary

**Database:** `immigration_agents_db` (MySQL via XAMPP)
**Scraper State:** Completed all 33 states, 1,202 cities
**Total Scraped (from state file):** 4,356 listings
**Last City Processed:** Silvassa, Dadra and Nagar Haveli (state index 32, city index 1)
**Status:** The scraper has gone through the entire city list once with a single query ("PTE IELTS Institute")

---

## 2. Project Architecture

### Files & Roles

| File | Purpose |
|------|---------|
| `batch_scraper.py` | **Main scraper** - city-by-city mode using Playwright + Chromium |
| `google_maps_scraper.py` | **Single query scraper** - one-off searches using Playwright + Firefox |
| `batch_config.json` | Configuration: queries, delays, states list, scroll settings |
| `scraper_state.json` | Resume state: tracks progress across cities/states |
| `cities_by_state.json` | 1,202 cities across 33 states/UTs |
| `city_coordinates.json` | Lat/long data for cities (141 KB) |
| `config.php` | DB config (root@localhost, no password) |
| `setup.php` | DB schema creation |
| `scraper.php` | PHP web UI for manual entry + duplicate check |
| `auto_scrape.php` | PHP web UI triggering Python scraper |
| `index.php` | Dashboard |
| `search.php` / `export.php` | Search/export functionality |
| `update_status_from_gmb.py` | GMB status checker |
| `update_address_fields.py` | Address parsing/extraction |

### Data Flow
```
batch_config.json → batch_scraper.py → Google Maps (Chromium) → MySQL DB
                                                                    ↓
                                         Web UI (PHP) ← search/export
```

---

## 3. Critical Issues Found

### ISSUE #1: No Map Zoom / Location Pinning (PRIMARY PROBLEM)

**Current behavior:** The scraper builds a URL-based search like `"PTE IELTS Institute in Bathinda, Punjab"` and types it into Google Maps search box. Google Maps interprets this as a text query and may show results from nearby areas or even different cities.

**What should happen:** The scraper should first navigate to the specific city coordinates, zoom into that location on the map, and THEN perform the search. This forces Google Maps to show results only within that geographic area.

**Impact:** Missing many local businesses because Google Maps is showing results for a broader area or sometimes even wrong cities.

**Root cause in code (`batch_scraper.py` lines 209-254):**
```python
# Current: Just types query in search box
search_query = f"{query} in {city}, {state}"
search_box.click()
page.keyboard.type(search_query, delay=50)
page.keyboard.press('Enter')
```

**Fix needed:** Use `city_coordinates.json` to navigate to exact coordinates first:
```
https://www.google.com/maps/@{lat},{lng},{zoom}z
```
Then clear search and type just the query. This way Google Maps restricts results to the visible map area.

---

### ISSUE #2: Only 1 Query Being Used

**Current `batch_config.json`:**
```json
"queries": ["PTE IELTS Institute"]
```

**Problem:** Only searching for "PTE IELTS Institute" - missing immigration consultants, visa consultants, study abroad consultants, and standalone PTE/IELTS centers.

**Fix needed:** Multiple query passes per city:
- "Immigration consultant"
- "Visa consultant"
- "IELTS coaching center"
- "PTE coaching center"
- "Study abroad consultant"
- "Overseas education consultant"

---

### ISSUE #3: Chromium vs Chrome Browser

**Current:** Uses Playwright's bundled Chromium (`p.chromium.launch()`)

**Problems with Chromium:**
- More easily detected as bot by Google
- No existing cookies/session = higher CAPTCHA risk
- Missing some proprietary codecs and features
- Leaves bot fingerprints

**Recommendation:** Use the user's actual Chrome browser via Playwright's `channel="chrome"` option:
```python
browser = p.chromium.launch(channel="chrome", headless=False)
```
This uses the real Chrome installation which has a more natural fingerprint and can leverage existing cookies.

---

### ISSUE #4: Duplicate Check is Incomplete

**Current duplicate logic (`batch_scraper.py` lines 422-430):**
- Only checks by phone number
- Does NOT check by business_name + city (unlike `google_maps_scraper.py` which does both)

**Impact:** If a business was scraped without a phone number, it could be re-inserted when found in another query.

**Additionally:** The `google_place_id` field uses timestamps (`gmaps_{timestamp}_{idx}`) instead of actual Google Place IDs, making it useless as a unique identifier.

---

### ISSUE #5: No Multi-Query Per City Strategy

The scraper picks ONE random query per city visit:
```python
query = random.choice(queries)  # line 539 in batch_scraper.py
```

This means each city only gets searched for ONE type of business. To cover all business types (immigration, IELTS, PTE, etc.), the scraper needs to run ALL queries for each city.

---

### ISSUE #6: Relevancy Filter May Be Too Aggressive

The `is_relevant_listing()` function (lines 128-167) excludes listings that match EXCLUDE_KEYWORDS like "bank", "hotel", etc. But some immigration consultants operate from hotel addresses or have "finance" in their services. This could be dropping valid results.

---

### ISSUE #7: Missing Data Fields

- **Email:** Never extracted (always empty)
- **Google Place ID:** Uses fake timestamps instead of actual IDs
- **Latitude/Longitude:** Always NULL for scraped entries
- **Review Count:** Always 0 (field exists but never populated)

---

### ISSUE #8: Rate Limiting & CAPTCHA Handling

- Delays are 10-30 seconds between cities (good)
- CAPTCHA detection exists but only stops the scraper - no retry or IP rotation
- No proxy support
- Running headless=false in config which is good for avoiding detection but slow

---

## 4. Database Analysis

**Schema Tables:**
1. `agents` - Main table with 15+ fields
2. `search_history` - Tracks completed searches

**From scraper_state.json:**
- 4,356 total scraped across all 1,202 cities
- That's only ~3.6 listings per city average
- Many small cities likely returned 0 results
- With only 1 query type, this represents maybe 20-30% of potential listings

**Estimated potential with proper implementation:** 15,000-25,000 listings (running all query types with proper map zooming)

---

## 5. What's Working Well

- State/city-based iteration with resume capability
- State file saves progress after each city (crash-resistant)
- Random delays between requests
- CAPTCHA detection
- Relevancy filtering (mostly good)
- Address/phone/pincode extraction
- PHP dashboard for viewing/exporting data
- Duplicate prevention (partial)

---

## 6. Recommended Action Plan

### Phase 1: Fix Core Scraping (High Priority)

1. **Implement map zoom-first approach:**
   - Load `city_coordinates.json`
   - Navigate to `google.com/maps/@{lat},{lng},14z` first
   - Wait for map to load
   - Then search within the zoomed area

2. **Use real Chrome instead of Chromium:**
   - Change to `p.chromium.launch(channel="chrome")`
   - Run in non-headless mode
   - Benefit from natural browser fingerprint

3. **Add all query types:**
   ```json
   "queries": [
     "Immigration consultant",
     "Visa consultant",
     "IELTS coaching center",
     "PTE coaching center",
     "Study abroad consultant"
   ]
   ```

4. **Run ALL queries per city (not random.choice):**
   - Iterate through each query for each city
   - Track which query+city combos are completed in state file

### Phase 2: Improve Data Quality

5. **Fix duplicate checking:** Add business_name + city check in batch_scraper.py
6. **Extract real Google Place IDs** from the GMB links
7. **Extract lat/long** from the map when viewing each listing
8. **Extract review count and rating** from listing details

### Phase 3: Scale

9. **Add proxy rotation** for avoiding CAPTCHAs
10. **Add email extraction** from business websites
11. **Implement retry logic** for CAPTCHA encounters (wait + retry)
12. **Better search_history tracking** to avoid re-scraping completed city+query combos

---

## 7. City-Based vs Pincode-Based Approach

**Current decision: City-based (correct)**

- 1,202 cities vs 155,000+ pin codes
- Cities cover the same geographic area much more efficiently
- Pin codes would take ~100x longer for marginal improvement
- The zoom-first approach will ensure coverage within each city

**Recommendation:** Stick with city-based, but for very large cities (Mumbai, Delhi, Bangalore, etc.), consider splitting into sub-areas/localities for better coverage.

---

## 8. Trial Run Outcome

I was unable to run the scraper in this sandbox environment because Google Maps blocks access from cloud/sandbox IPs. The scraper needs to run on your local machine (XAMPP setup) with your actual Chrome browser. This is actually further evidence that using real Chrome (`channel="chrome"`) on your local machine is the right approach.

---

**Next Step:** Once you review this report, we can start implementing the fixes starting with the zoom-first approach and multi-query strategy.
