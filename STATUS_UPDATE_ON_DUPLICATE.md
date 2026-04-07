# Status Update on Duplicate Records

## Overview

When the scraper finds a business that already exists in the database, it now checks if the status has changed and updates it accordingly. This ensures the database always reflects the current operational status of businesses.

---

## How It Works

### 1. Duplicate Detection
The scraper checks for duplicates using two methods:
- **By phone number** (primary identifier)
- **By business name + city** (fallback if no phone)

### 2. Status Comparison
If a duplicate is found:
- Compare existing `status` in database with newly scraped `status`
- If different, update the record with new status
- If same, skip without changes

### 3. Status Update
When status changes:
- Update the database record
- Log the change with before/after values
- Include in summary statistics

---

## Code Implementation

### Updated Function: `check_duplicate_and_update_status()`

**Location:** `batch_scraper.py` (lines 99-130)

```python
def check_duplicate_and_update_status(self, cursor, data):
    """Check if entry already exists and update status if different"""
    phone = data.get('phone')
    business_name = data.get('business_name')
    city = data.get('city')
    new_status = data.get('status', 'active')

    existing_record = None

    # Check by phone first
    if phone:
        cursor.execute("SELECT id, status FROM agents WHERE phone = %s", (phone,))
        existing_record = cursor.fetchone()

    # If not found by phone, check by business_name + city
    if not existing_record and business_name and city:
        cursor.execute("SELECT id, status FROM agents WHERE business_name = %s AND city = %s",
                      (business_name, city))
        existing_record = cursor.fetchone()

    if existing_record:
        record_id = existing_record[0]
        old_status = existing_record[1]

        # Update status if different
        if old_status != new_status:
            cursor.execute("UPDATE agents SET status = %s WHERE id = %s", (new_status, record_id))
            return {'success': False, 'message': 'Duplicate', 'status_updated': True, 'old_status': old_status, 'new_status': new_status}
        else:
            return {'success': False, 'message': 'Duplicate', 'status_updated': False}

    return None
```

---

## Use Cases

### Use Case 1: Business Closes Temporarily
**Initial scrape:**
```
Business: ABC Immigration Services
Status: active
Phone: +91-9876543210
```

**Later scrape (business temporarily closed):**
```
Found duplicate: +91-9876543210
Old status: active
New status: temporarily closed
Action: UPDATE status
```

**Database result:**
```sql
UPDATE agents SET status = 'temporarily closed' WHERE phone = '+91-9876543210';
```

### Use Case 2: Temporarily Closed Reopens
**Initial scrape:**
```
Business: XYZ Consultants
Status: temporarily closed
Phone: +91-1234567890
```

**Later scrape (business reopened):**
```
Found duplicate: +91-1234567890
Old status: temporarily closed
New status: active
Action: UPDATE status
```

**Database result:**
```sql
UPDATE agents SET status = 'active' WHERE phone = '+91-1234567890';
```

### Use Case 3: Business Closes Permanently
**Initial scrape:**
```
Business: Old Town IELTS
Status: active
Phone: +91-9988776655
```

**Later scrape (business permanently closed):**
```
Found duplicate: +91-9988776655
Old status: active
New status: permanently closed
Action: UPDATE status
```

**Database result:**
```sql
UPDATE agents SET status = 'permanently closed' WHERE phone = '+91-9988776655';
```

### Use Case 4: No Status Change
**Initial scrape:**
```
Business: Global Immigration
Status: active
Phone: +91-5544332211
```

**Later scrape (still active):**
```
Found duplicate: +91-5544332211
Old status: active
New status: active
Action: SKIP (no change)
```

**Database result:**
No update needed.

---

## Console Output

### Status Updated
```
[15/78] Processing...
  🖱️  Clicking ABC Immigration Services for accurate details...
  ✓ ABC Immigration Services
    🎯 Services: immigration consultant
    ⚠️  Status: temporarily closed
    📞 +91-9876543210

💾 Database: Saved 12 new, Skipped 3 duplicates, Updated 1 statuses
  ✓ Updated status: ABC Immigration Services [active → temporarily closed]
```

### Multiple Status Updates
```
[35/78] Processing...
  ⏸️  Old Town IELTS - Status: Permanently closed
  🖱️  Clicking Old Town IELTS for accurate details...
  ✓ Old Town IELTS
    🎯 Services: ielts coaching
    ⚠️  Status: permanently closed
    📞 +91-1234567890

💾 Database: Saved 8 new, Skipped 5 duplicates, Updated 3 statuses
  ✓ Updated status: ABC Immigration Services [active → temporarily closed]
  ✓ Updated status: XYZ Consultants [temporarily closed → active]
  ✓ Updated status: Old Town IELTS [active → permanently closed]
```

### No Status Updates
```
💾 Database: Saved 15 new, Skipped 8 duplicates
```

---

## Benefits

### 1. ✅ Always Current
- Database reflects real-time business status
- No manual updates needed
- Automatic status tracking

### 2. ✅ Historical Tracking
You can track status changes over time by adding a history table:

```sql
CREATE TABLE status_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_id INT,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);
```

### 3. ✅ Business Intelligence
Track patterns:
- Which businesses close temporarily vs permanently?
- How long do temporary closures last?
- Which locations have higher closure rates?

### 4. ✅ CRM Integration
Keep your CRM up to date:
- Auto-pause campaigns for closed businesses
- Re-enable campaigns when businesses reopen
- Filter out permanently closed from outreach

---

## Status Change Tracking Query

### Recent Status Changes
```sql
SELECT
    business_name,
    city,
    state,
    status,
    modified_date
FROM agents
WHERE modified_date > DATE_SUB(NOW(), INTERVAL 7 DAY)
  AND status != 'active'
ORDER BY modified_date DESC;
```

### Businesses That Reopened
To find businesses that reopened, you would need a status history table, or check scraped_date:

```sql
SELECT
    business_name,
    city,
    phone,
    status,
    scraped_date
FROM agents
WHERE status = 'active'
  AND scraped_date > DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY scraped_date DESC;
```

### Closure Rate by City
```sql
SELECT
    city,
    state,
    COUNT(*) as total_businesses,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count,
    COUNT(CASE WHEN status != 'active' THEN 1 END) as closed_count,
    ROUND(COUNT(CASE WHEN status != 'active' THEN 1 END) * 100.0 / COUNT(*), 2) as closure_rate
FROM agents
GROUP BY city, state
HAVING total_businesses > 10
ORDER BY closure_rate DESC;
```

---

## Return Values

### New Record
```python
{
    'success': True,
    'id': 12345
}
```

### Duplicate (No Change)
```python
{
    'success': False,
    'message': 'Duplicate',
    'status_updated': False
}
```

### Duplicate (Status Updated)
```python
{
    'success': False,
    'message': 'Duplicate',
    'status_updated': True,
    'old_status': 'active',
    'new_status': 'temporarily closed'
}
```

---

## Statistics Summary

### Example Output
```
💾 Database: Saved 45 new, Skipped 23 duplicates, Updated 7 statuses
  ✓ Updated status: ABC Immigration [active → temporarily closed]
  ✓ Updated status: XYZ Consultants [temporarily closed → active]
  ✓ Updated status: Global IELTS [active → permanently closed]
  ✓ Updated status: Smart PTE [temporarily closed → active]
  ✓ Updated status: Old Town Visa [active → permanently closed]
  ✓ Updated status: City Immigration [temporarily closed → permanently closed]
  ✓ Updated status: New Era Consultants [temporarily closed → active]
```

---

## Edge Cases Handled

### 1. Phone Number Changes
If a business changes phone number but keeps same name/city:
- New record will be created (different phone)
- Old record remains with old status
- Both records exist (historical data preserved)

### 2. Name Changes
If a business changes name but keeps same phone:
- Duplicate detected by phone
- Status updated if changed
- Name remains as originally scraped

### 3. Location Changes
If a business moves to different city but keeps same phone:
- Duplicate detected by phone
- Status updated if changed
- City remains as originally scraped

### 4. New Business Same Name/City
If different business with same name in same city:
- Will be detected as duplicate (by name+city)
- Could incorrectly update status
- **Mitigation:** Phone number is checked first (more reliable)

---

## Database Schema Requirements

Ensure the `agents` table has:
```sql
ALTER TABLE agents ADD COLUMN status VARCHAR(50) DEFAULT 'active';
ALTER TABLE agents ADD COLUMN modified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
```

The `modified_date` column automatically updates when any field changes, helping track when status was last updated.

---

## Monitoring

### Check Recent Status Updates
```bash
# Count status updates in last scrape
grep "Updated status:" scraper.log | wc -l

# Show which businesses had status updated
grep "Updated status:" scraper.log
```

### Status Update Statistics
```sql
SELECT
    DATE(modified_date) as date,
    COUNT(*) as records_modified,
    COUNT(CASE WHEN status != 'active' THEN 1 END) as now_closed,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as now_active
FROM agents
WHERE modified_date > DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(modified_date)
ORDER BY date DESC;
```

---

## Integration Example

### Automated Email Alerts
Send email when status changes to closed:

```python
if result.get('status_updated') and result.get('new_status') != 'active':
    send_notification(
        f"Business Closed: {agent.get('business_name')}",
        f"Status changed from {result.get('old_status')} to {result.get('new_status')}"
    )
```

### CRM Webhook
Trigger CRM update when status changes:

```python
if result.get('status_updated'):
    webhook_data = {
        'business_name': agent.get('business_name'),
        'phone': agent.get('phone'),
        'old_status': result.get('old_status'),
        'new_status': result.get('new_status'),
        'updated_at': datetime.now().isoformat()
    }
    requests.post('https://your-crm.com/webhook', json=webhook_data)
```

---

## Summary

✅ **Automatic Updates:** Status changes detected and updated automatically
✅ **Duplicate Handling:** No duplicate records created, only status updated
✅ **Detailed Logging:** Shows which businesses had status changed
✅ **Statistics:** Summary shows count of status updates
✅ **Historical Data:** Can track status changes over time
✅ **CRM Integration:** Keep external systems synchronized

**Result:** Database always reflects current business status! 🎯
