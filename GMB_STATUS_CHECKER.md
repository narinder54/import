# GMB Status Checker Script

## Overview

This script scans through all existing database records, visits each Google Maps Business (GMB) link, and checks if the business is closed. If found closed, it updates the status in the database.

---

## Purpose

You may have scraped data **before** the status tracking feature was added. This script retroactively checks all existing records and updates their status.

---

## Usage

### Test Mode (First 10 Records)
```bash
python3 update_status_from_gmb.py --test
```

### Full Scan (All Records)
```bash
python3 update_status_from_gmb.py
```

### Start from Specific Record
```bash
python3 update_status_from_gmb.py --start 500
```

### Process Specific Batch Size
```bash
python3 update_status_from_gmb.py --batch 100
```

### Combine Options
```bash
# Start from record 500, process 200 records
python3 update_status_from_gmb.py --start 500 --batch 200
```

---

## Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--test` | Test mode - check first 10 records only | `--test` |
| `--start N` | Start from record number N (0-indexed) | `--start 500` |
| `--batch N` | Process only N records | `--batch 100` |

---

## How It Works

### 1. Database Query
```sql
SELECT id, business_name, city, state, gmb_link, status
FROM agents
WHERE gmb_link IS NOT NULL
  AND gmb_link != ''
  AND status = 'active'
ORDER BY id ASC
```
Only checks records that:
- Have a GMB link
- Are currently marked as 'active'

### 2. Visit GMB Link
For each record, the script:
- Opens the GMB link in a headless browser
- Waits for page to load
- Extracts page content

### 3. Check for Closure
Looks for these indicators in the page:
- `"temporarily closed"` → Status: `temporarily closed`
- `"permanently closed"` → Status: `permanently closed`
- Neither found → Status remains: `active`

### 4. Update Database
If closed status found:
```sql
UPDATE agents SET status = 'temporarily closed' WHERE id = 123;
```

---

## Console Output

### Starting the Script
```
======================================================================
🔍 GMB STATUS CHECKER - Scanning Database for Closed Businesses
======================================================================

✅ Connected to database
📊 Found 5275 active agents with GMB links

----------------------------------------------------------------------

🌐 Launching browser...
```

### Processing Records
```
[1/5275] Checking: ABC Immigration Services
  📍 Mumbai, Maharashtra
  ✅ Still active

[2/5275] Checking: XYZ Visa Consultants
  📍 Delhi, Delhi
  ⏸️  TEMPORARILY CLOSED - Updating database

[3/5275] Checking: Old Town IELTS
  📍 Jaipur, Rajasthan
  ⛔ PERMANENTLY CLOSED - Updating database

[4/5275] Checking: Global Education Services
  📍 Bangalore, Karnataka
  ✅ Still active
```

### Progress Report (Every 50 Records)
```
----------------------------------------
📊 Progress: 50/5275 checked
   ✅ Active: 45
   ⏸️  Temp Closed: 3
   ⛔ Perm Closed: 2
----------------------------------------
```

### Final Summary
```
======================================================================
📊 FINAL SUMMARY
======================================================================
  📋 Total records in database: 5275
  🔍 Records checked: 5275
  ✅ Still active: 4892
  ⏸️  Updated to 'temporarily closed': 298
  ⛔ Updated to 'permanently closed': 85
  ⚠️  No GMB link: 0
  ❌ Errors: 0
======================================================================

✅ Updated 383 business statuses in database!
```

---

## Performance

### Speed
- ~2-3 seconds per record (page load + delay)
- ~50 records per 2-3 minutes
- ~1000 records per 40-60 minutes
- ~5000 records per 3-5 hours

### Why Headless?
The script runs in headless mode (no visible browser) for:
- Faster execution
- Lower memory usage
- Can run in background

### Anti-Detection
- Random delays between requests (1.5-3 seconds)
- Standard user agent
- Normal browser viewport

---

## Recommended Approach

### For Large Databases (5000+ records)

**Option 1: Run in Background**
```bash
nohup python3 update_status_from_gmb.py > status_check.log 2>&1 &
```

**Option 2: Run in Batches**
```bash
# Batch 1: Records 0-1000
python3 update_status_from_gmb.py --batch 1000

# Batch 2: Records 1000-2000
python3 update_status_from_gmb.py --start 1000 --batch 1000

# Batch 3: Records 2000-3000
python3 update_status_from_gmb.py --start 2000 --batch 1000
```

**Option 3: Run Overnight**
```bash
python3 update_status_from_gmb.py
# Let it run overnight
```

---

## Error Handling

### Network Errors
If a page fails to load:
- Error is logged
- Record is skipped
- Script continues to next record

### Database Errors
If status update fails:
- Error is logged
- Script continues
- Can retry later

### Keyboard Interrupt
Press `Ctrl+C` to stop:
- Current progress is saved
- Summary is displayed
- Can resume with `--start`

---

## Recovery

### If Script Stops Mid-Way

1. **Check how many were processed:**
   ```sql
   SELECT COUNT(*) FROM agents WHERE status != 'active';
   ```

2. **Resume from where you left off:**
   ```bash
   # If stopped at record 1500
   python3 update_status_from_gmb.py --start 1500
   ```

### Re-Run Safely
The script only checks records with `status = 'active'`, so running it multiple times is safe - already-updated records won't be re-checked.

---

## Verification

### After Running the Script

**Check status distribution:**
```sql
SELECT status, COUNT(*) as count
FROM agents
GROUP BY status
ORDER BY count DESC;
```

**Expected output:**
```
| status              | count |
|---------------------|-------|
| active              | 4892  |
| temporarily closed  | 298   |
| permanently closed  | 85    |
```

**Check recently updated:**
```sql
SELECT business_name, city, status
FROM agents
WHERE status != 'active'
ORDER BY id DESC
LIMIT 20;
```

---

## Scheduling

### Run Weekly (Cron)
```bash
# Edit crontab
crontab -e

# Add line to run every Sunday at 2 AM
0 2 * * 0 cd /Applications/XAMPP/xamppfiles/htdocs/import && python3 update_status_from_gmb.py >> /var/log/gmb_check.log 2>&1
```

### Run Monthly
```bash
# Run on 1st of each month at 3 AM
0 3 1 * * cd /Applications/XAMPP/xamppfiles/htdocs/import && python3 update_status_from_gmb.py >> /var/log/gmb_check.log 2>&1
```

---

## Troubleshooting

### "No GMB link" for Many Records
Some records may not have GMB links. The script skips these automatically.

### "Error checking page" Messages
Usually means:
- Page took too long to load
- Google blocked the request temporarily
- Invalid GMB link

**Solution:** Increase delay or run in smaller batches.

### Database Connection Error
Check:
- MySQL is running
- Socket path is correct
- Database name is correct

### Browser Launch Error
Check:
- Playwright is installed: `pip install playwright`
- Browsers are installed: `playwright install firefox`

---

## Files

### Main Script
- `/Applications/XAMPP/xamppfiles/htdocs/import/update_status_from_gmb.py`

### Log Output (if using nohup)
- `status_check.log`

---

## Summary

✅ **Purpose:** Check existing records for closed businesses
✅ **Method:** Visit GMB link, check for closure text
✅ **Speed:** ~2-3 seconds per record
✅ **Safe:** Only checks 'active' records, can run multiple times
✅ **Resumable:** Use `--start` to continue from where you left off
✅ **Headless:** Runs in background without visible browser

**Run this script once to update all your existing data, then the main scraper will handle new records automatically!** 🎯
