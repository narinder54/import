# Business Status Tracking Feature

## Overview

The scraper now detects and tracks business closure status instead of skipping closed businesses. This allows you to maintain a complete database with status indicators for filtering and follow-up.

---

## Status Types

### 1. **active** (Default)
Normal operating businesses without closure indicators.

### 2. **temporarily closed**
Businesses showing temporary closure status on Google Maps.

**Indicators:**
- "temporarily closed"
- "temp closed"

### 3. **permanently closed**
Businesses that have shut down permanently.

**Indicators:**
- "permanently closed"
- "closed permanently"
- "permanently shut"
- "closed down"

---

## How It Works

### Detection Process

**Step 1: Extract Listing Text**
```python
listing_text = listing.inner_text()
listing_text_lower = listing_text.lower()
```

**Step 2: Determine Status**
```python
business_status = 'active'  # Default

if 'temporarily closed' in listing_text_lower or 'temp closed' in listing_text_lower:
    business_status = 'temporarily closed'
elif 'permanently closed' in listing_text_lower or ...:
    business_status = 'permanently closed'
```

**Step 3: Save with Status**
```python
agent_data = {
    'business_name': business_name,
    'address': address,
    'phone': phone,
    'city': city,
    'state': state,
    ...
    'status': business_status  # Saved to database
}
```

---

## Database Schema

### Status Column
```sql
status VARCHAR(50) DEFAULT 'active'
```

**Possible values:**
- `'active'` - Normal operating business
- `'temporarily closed'` - Temporarily suspended operations
- `'permanently closed'` - Permanently shut down

---

## Console Output

### Active Business
```
[5/78] Processing...
  🖱️  Clicking ABC Immigration Services for accurate details...
  ✓ ABC Immigration Services
    🏷️  Category: Immigration consultant
    🎯 Services: immigration consultant, study abroad consultant
    📞 +91-9876543210
```

### Temporarily Closed Business
```
[8/78] Processing...
  ⏸️  Old Town IELTS - Status: Temporarily closed
  🖱️  Clicking Old Town IELTS for accurate details...
  ✓ Old Town IELTS
    🏷️  Category: IELTS coaching
    🎯 Services: ielts coaching
    ⚠️  Status: temporarily closed
    📞 +91-1234567890
```

### Permanently Closed Business
```
[12/78] Processing...
  ⏸️  Defunct Visas Ltd - Status: Permanently closed
  🖱️  Clicking Defunct Visas Ltd for accurate details...
  ✓ Defunct Visas Ltd
    🏷️  Category: Visa consultant
    🎯 Services: visa consultant
    ⚠️  Status: permanently closed
    📞 +91-9988776655
```

---

## Benefits

### 1. ✅ Complete Database
- All businesses are saved, regardless of status
- No data loss from skipping closed businesses
- Historical record of all businesses found

### 2. ✅ Flexible Filtering
You can filter by status when querying:

```sql
-- Active businesses only
SELECT * FROM agents WHERE status = 'active';

-- Temporarily closed (for follow-up)
SELECT * FROM agents WHERE status = 'temporarily closed';

-- All closed businesses
SELECT * FROM agents WHERE status != 'active';
```

### 3. ✅ Follow-up Opportunities
- **Temporarily closed:** Can check back later when they reopen
- **Permanently closed:** Remove from outreach list
- **Active:** Primary outreach targets

### 4. ✅ Analytics
Track closure rates:

```sql
-- Closure statistics
SELECT
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM agents
GROUP BY status;
```

**Example output:**
```
| status              | count | percentage |
|---------------------|-------|------------|
| active              | 4,892 | 92.74%     |
| temporarily closed  | 298   | 5.65%      |
| permanently closed  | 85    | 1.61%      |
```

---

## Database Queries

### Count by Status
```sql
SELECT status, COUNT(*) as total
FROM agents
GROUP BY status
ORDER BY total DESC;
```

### Active Businesses Only (for CRM export)
```sql
SELECT
    business_name,
    phone,
    website,
    city,
    state,
    services
FROM agents
WHERE status = 'active'
ORDER BY city, state;
```

### Temporarily Closed (follow-up list)
```sql
SELECT
    business_name,
    phone,
    city,
    state,
    gmb_link
FROM agents
WHERE status = 'temporarily closed'
ORDER BY city, state;
```

### Recently Added Closed Businesses
```sql
SELECT
    business_name,
    city,
    status,
    scraped_date
FROM agents
WHERE status != 'active'
ORDER BY scraped_date DESC
LIMIT 50;
```

---

## PHP Integration

### Display Status Badge
```php
<?php
$status_class = $agent['status'] == 'active' ? 'badge-success' : 'badge-warning';
$status_text = ucfirst($agent['status']);
?>
<span class="badge <?php echo $status_class; ?>">
    <?php echo $status_text; ?>
</span>
```

### Filter Active Only
```php
$active_agents = $scraper->getAgentsByStatus('active');
```

### Count by Status
```php
$status_counts = [
    'active' => $scraper->countByStatus('active'),
    'temporarily_closed' => $scraper->countByStatus('temporarily closed'),
    'permanently_closed' => $scraper->countByStatus('permanently closed')
];
```

---

## Export Considerations

### CRM Export (Active Only)
When exporting to CSV for CRM:
```php
$query = "SELECT * FROM agents WHERE status = 'active'";
```

### Full Database Export (All Statuses)
When backing up or analyzing:
```php
$query = "SELECT * FROM agents ORDER BY status, city";
```

### Status Column in Export
Include status column for reference:
```csv
business_name,phone,city,state,status
ABC Immigration,+91-9876543210,Mumbai,Maharashtra,active
Old Town IELTS,+91-1234567890,Delhi,Delhi,temporarily closed
```

---

## Statistics Tracking

### Overall Completion Rate
```sql
SELECT
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count,
    COUNT(CASE WHEN status = 'temporarily closed' THEN 1 END) as temp_closed_count,
    COUNT(CASE WHEN status = 'permanently closed' THEN 1 END) as perm_closed_count,
    COUNT(*) as total_count,
    ROUND(COUNT(CASE WHEN status = 'active' THEN 1 END) * 100.0 / COUNT(*), 2) as active_percentage
FROM agents;
```

### Status by State
```sql
SELECT
    state,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
    COUNT(CASE WHEN status = 'temporarily closed' THEN 1 END) as temp_closed,
    COUNT(CASE WHEN status = 'permanently closed' THEN 1 END) as perm_closed,
    COUNT(*) as total
FROM agents
GROUP BY state
ORDER BY total DESC;
```

### Status by Service Type
```sql
SELECT
    services,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
    COUNT(CASE WHEN status != 'active' THEN 1 END) as closed,
    COUNT(*) as total
FROM agents
GROUP BY services
ORDER BY total DESC;
```

---

## Use Cases

### 1. Primary Outreach Campaign
Target only active businesses:
```sql
SELECT business_name, phone, email, website
FROM agents
WHERE status = 'active' AND phone IS NOT NULL
ORDER BY state, city;
```

### 2. Follow-up Campaign
Check temporarily closed businesses after 3 months:
```sql
SELECT business_name, phone, gmb_link, scraped_date
FROM agents
WHERE status = 'temporarily closed'
  AND scraped_date < DATE_SUB(NOW(), INTERVAL 3 MONTH);
```

### 3. Database Cleanup
Remove permanently closed businesses after verification:
```sql
DELETE FROM agents
WHERE status = 'permanently closed'
  AND scraped_date < DATE_SUB(NOW(), INTERVAL 6 MONTH);
```

### 4. Market Analysis
Analyze closure rates by location:
```sql
SELECT
    state,
    city,
    COUNT(*) as total_businesses,
    COUNT(CASE WHEN status != 'active' THEN 1 END) as closed_businesses,
    ROUND(COUNT(CASE WHEN status != 'active' THEN 1 END) * 100.0 / COUNT(*), 2) as closure_rate
FROM agents
GROUP BY state, city
HAVING total_businesses > 10
ORDER BY closure_rate DESC;
```

---

## Comparison

### Before (Skip Closed)
```
Total scraped: 1,000 listings
- Active: 920 (saved)
- Closed: 80 (skipped - lost data)

Database: 920 records
```

### After (Track Status)
```
Total scraped: 1,000 listings
- Active: 920 (saved with status='active')
- Temporarily closed: 60 (saved with status='temporarily closed')
- Permanently closed: 20 (saved with status='permanently closed')

Database: 1,000 records
```

**Benefit:** 80 additional records (8% more data) for analysis and follow-up.

---

## Index Page Update

Update the stats query to show active count:
```php
$stats['active_agents'] = $conn->query(
    "SELECT COUNT(*) as count FROM agents WHERE status = 'active'"
)->fetch_assoc()['count'];
```

Display both totals:
```html
<div class="stat-card">
    <h3>Total Businesses</h3>
    <p class="stat-number"><?php echo number_format($total); ?></p>
</div>
<div class="stat-card">
    <h3>Active Businesses</h3>
    <p class="stat-number"><?php echo number_format($active); ?></p>
</div>
```

---

## Summary

✅ **Detection:** Automatically detects closure status from listing text
✅ **Classification:** Three status types (active, temporarily closed, permanently closed)
✅ **Storage:** Status saved to database for filtering
✅ **Flexibility:** Can filter by status for different use cases
✅ **Analytics:** Track closure rates by location/service
✅ **Complete Data:** No business data is lost by skipping
✅ **Follow-up:** Can re-check temporarily closed businesses later

**Result:** Complete database with actionable status tracking! 🎯
