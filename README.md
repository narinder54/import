# Immigration Agents Database System

A comprehensive web application for scraping, managing, and exporting immigration agent data from Google Maps.

## Features

- **Automated Google Maps Scraping** - Uses Playwright for browser automation
- **Duplicate Prevention** - Automatically checks for existing entries
- **Web Dashboard** - View statistics and manage agents
- **Advanced Search** - Filter by city, state, PIN code, and services
- **CSV Export** - Export all or filtered results
- **Manual Entry** - Add agents manually through web form
- **Batch Processing** - Scrape multiple cities automatically

---

## System Requirements

- **PHP** 7.4+ (XAMPP includes this)
- **MySQL** 5.7+ (XAMPP includes this)
- **Python** 3.8+ (✓ Installed: Python 3.9.6)
- **Playwright** (✓ Installed)

---

## Installation Status

✅ **COMPLETE** - All dependencies installed and configured!

### What's Been Installed:

1. ✓ Python 3.9.6
2. ✓ Playwright 1.57.0
3. ✓ PyMySQL 1.1.2
4. ✓ Chromium Browser (for scraping)
5. ✓ All PHP files configured

---

## Getting Started

### Step 1: Initialize Database

1. Start XAMPP (Apache + MySQL)
2. Open browser and visit: `http://localhost/import/setup.php`
3. This creates the database and tables

### Step 2: Start Using the System

**Main Pages:**

- **Dashboard**: `http://localhost/import/index.php`
- **Auto Scraper**: `http://localhost/import/auto_scrape.php`
- **Manual Entry**: `http://localhost/import/scraper.php`
- **Search**: `http://localhost/import/search.php`
- **Export**: `http://localhost/import/export.php`

---

## Usage Guide

### Automated Scraping (Recommended)

1. Visit: `http://localhost/import/auto_scrape.php`
2. Choose an option:

**Option A: Quick Start Templates**
- Click on any template card (Immigration, IELTS, PTE, Visa)
- Automatically scrapes multiple major cities
- Watch real-time progress

**Option B: Custom Search**
- Enter query: "immigration consultant"
- Enter location: "Delhi"
- Set max results: 20
- Click "Start Scraping"

### Manual Entry

1. Visit: `http://localhost/import/scraper.php`
2. Fill in the form with business details
3. Submit to add to database

### Search & Filter

1. Visit: `http://localhost/import/search.php`
2. Filter by:
   - City (e.g., Delhi, Mumbai)
   - State (e.g., Maharashtra)
   - PIN Code
   - Services (Immigration, IELTS, PTE)
3. View filtered results
4. Export filtered results to CSV

### Export Data

1. Visit: `http://localhost/import/export.php`
2. Preview data to be exported
3. Click "Download CSV File"
4. Opens in Excel with proper formatting

---

## File Structure

```
/import/
├── config.php              # Database configuration
├── setup.php               # Database initialization
├── index.php               # Main dashboard
├── scraper.php             # Manual entry & scraper foundation
├── auto_scrape.php         # Automated scraping interface
├── search.php              # Search and filter page
├── export.php              # CSV export functionality
├── style.css               # Styling
├── google_maps_scraper.py  # Python scraping script
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## Database Structure

**Table: agents**
- Business information (name, address, phone)
- Location data (city, state, PIN code)
- Contact details (website, email)
- Services offered
- Scraping metadata

**Table: search_history**
- Tracks completed searches
- Prevents re-scraping same locations

---

## How Duplicate Prevention Works

The system checks for duplicates using:

1. **Phone Number** (primary check)
   - Most reliable unique identifier
   - Checked before every insert

2. **Business Name + City** (secondary check)
   - Prevents duplicates when phone is missing
   - Case-sensitive comparison

If a duplicate is detected:
- Entry is skipped
- Counter increments
- Logged in output

---

## Scraping Best Practices

### Avoid CAPTCHAs:

1. **Limit results per search** - Keep to 20-30
2. **Add delays between cities** - Built-in 3-second delay
3. **Use headless mode** - Less detectable (default ON)
4. **Don't over-scrape** - Space out scraping sessions
5. **Vary search times** - Don't scrape at fixed intervals

### Recommended Approach:

- Scrape 1-2 cities per day
- Use different queries (immigration, visa, IELTS)
- Review and clean data regularly
- Manually verify important entries

---

## Troubleshooting

### Python Script Not Running:

```bash
# Test Python script manually
cd /Applications/XAMPP/xamppfiles/htdocs/import
python3 google_maps_scraper.py "immigration consultant" "Delhi" 5 true
```

### Playwright Not Found:

```bash
# Reinstall Playwright
pip3 install playwright
/Users/narinder/Library/Python/3.9/bin/playwright install chromium
```

### Database Connection Error:

1. Check XAMPP MySQL is running
2. Verify database exists: `immigration_agents_db`
3. Check credentials in [config.php](config.php)

### CAPTCHA Issues:

- Reduce max_results to 10-15
- Increase delays in Python script
- Use headless mode
- Consider using proxy rotation

---

## Command Line Usage

You can also run the Python scraper directly from terminal:

```bash
# Basic usage
python3 google_maps_scraper.py "immigration consultant" "Delhi" 20 true

# Arguments:
# 1. Query (e.g., "immigration consultant")
# 2. Location (e.g., "Delhi")
# 3. Max results (default: 20)
# 4. Headless mode (true/false, default: true)

# Examples:
python3 google_maps_scraper.py "IELTS coaching" "Mumbai" 30 false
python3 google_maps_scraper.py "PTE coaching" "Bangalore" 15 true
```

---

## Data Export Format

CSV exports include:
- Business Name
- Complete Address
- Phone Number
- City, State, PIN Code
- Website
- Email
- Services Offered
- Source Location (search query used)
- Date Added

---

## Security Notes

1. **Database Credentials** - Default XAMPP setup (root, no password)
   - Consider changing for production use

2. **Web Scraping** - Review robots.txt and ToS
   - Use responsibly and ethically
   - Only scrape publicly available data

3. **Data Privacy** - Handle contact information responsibly
   - Comply with data protection regulations
   - Use for legitimate B2B purposes only

---

## Future Enhancements (Optional)

- Email extraction from websites
- Social media profile links
- Business ratings and reviews
- Automated daily scraping schedule
- Proxy rotation for large-scale scraping
- Email marketing integration
- CRM integration
- Duplicate merge functionality

---

## Support

For issues or questions:
1. Check this README
2. Review PHP error logs in XAMPP
3. Check Python script output for errors
4. Test individual components separately

---

## Technical Details

**Python Libraries:**
- `playwright` - Browser automation
- `pymysql` - MySQL database connection
- `python-dotenv` - Environment configuration

**PHP Features:**
- MySQLi for database operations
- cURL for HTTP requests (manual scraping)
- Shell execution for Python integration
- JSON for data exchange

**Database:**
- MySQL 5.7+ compatible
- UTF-8 character encoding
- Indexed for fast searching

---

## License

This project is for educational and business use.
Use responsibly and comply with applicable laws and regulations.

---

## Version

**Version**: 1.0
**Last Updated**: January 2026
**Status**: Production Ready ✓

---

**Created for Immigration Industry B2B Sales**
All systems operational and ready to use!
