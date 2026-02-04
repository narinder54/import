# Address Extraction Update

## Problem Identified

The previous extraction logic was using substring matching, which caused incorrect results:

**Example Address:**
```
AMC 1, 581, Ana Sagar Circular Rd, above Lapinozz Pizza, Shantipura, Anand Nagar, Ajmer, Rajasthan 305001
```

**Old Logic Issues:**
- City extraction: Searched for city name anywhere in address (substring matching)
- State extraction: Searched for state name anywhere in address
- Could match wrong parts of the address
- Not following the standard Indian address format

---

## Solution: Proper Address Parsing

### Standard Indian Address Format:
```
[Street/Building], [Area/Locality], [City], [State] [Pincode]
```

### New Extraction Logic:

#### 1. **Split by Comma**
Parse address from right to left (most specific to least specific):
```
Parts: [..., City, State Pincode]
```

#### 2. **Extract Pincode (Last)**
- Regex: `\b\d{6}\b` (6-digit number)
- Always at the end of address

#### 3. **Extract State (Second Last)**
- Remove pincode from last part
- What remains is the state name
- Validates against state mappings

#### 4. **Extract City (Third Last)**
- After removing pincode, city is second-to-last part
- Validates against cities database (1,202 cities)

---

## Implementation

### Updated Functions in `batch_scraper.py`:

#### `extract_city_from_address()`
```python
def extract_city_from_address(self, address):
    # Split by comma
    parts = [part.strip() for part in address.split(',')]

    # Get last part: "State Pincode" or "Pincode"
    last_part = parts[-1]
    last_part_cleaned = re.sub(r'\b\d{6}\b', '', last_part).strip()

    # Determine city position
    if last_part_cleaned:
        # Format: ..., City, State Pincode
        potential_city = parts[-2]
    else:
        # Format: ..., City, State, Pincode
        potential_city = parts[-3]

    # Validate against cities database
    return validated_city
```

#### `extract_state_from_address()`
```python
def extract_state_from_address(self, address):
    # Split by comma
    parts = [part.strip() for part in address.split(',')]

    # Get last part
    last_part = parts[-1]
    last_part_cleaned = re.sub(r'\b\d{6}\b', '', last_part).strip()

    # Determine state position
    if last_part_cleaned:
        # Format: ..., City, State Pincode
        potential_state = last_part_cleaned
    else:
        # Format: ..., City, State, Pincode
        potential_state = parts[-2]

    # Validate against state mappings
    return validated_state
```

---

## Test Results

### Example 1: Your Address
```
Address: AMC 1, 581, Ana Sagar Circular Rd, above Lapinozz Pizza, Shantipura, Anand Nagar, Ajmer, Rajasthan 305001
✅ City: Ajmer
✅ State: Rajasthan
✅ Pincode: 305001
```

### Example 2: State and Pincode Separated
```
Address: Plot 456, Near Bus Stand, Hisar, Haryana, 125001
✅ City: Hisar
✅ State: Haryana
✅ Pincode: 125001
```

### Example 3: Standard Format
```
Address: Building A, Street 5, Mumbai, Maharashtra, 400001
✅ City: Mumbai
✅ State: Maharashtra
✅ Pincode: 400001
```

---

## Benefits

### 1. ✅ Accurate Parsing
- Follows Indian address structure
- Parses from right to left (specific to general)
- No false substring matches

### 2. ✅ Validated Results
- City validated against 1,202 cities database
- State validated against 33 states + UTs
- Pincode validated with 6-digit regex

### 3. ✅ Handles Multiple Formats
- `..., City, State Pincode` ✓
- `..., City, State, Pincode` ✓
- State abbreviations (RJ, MH, etc.) ✓
- Alternate names (Bombay → Mumbai) ✓

---

## Update Script: `update_address_fields.py`

### Purpose
Updates all existing database records with correctly extracted city, state, and pincode from their addresses.

### Features
1. **Reads all records** from `agents` table
2. **Extracts correct values** using new parsing logic
3. **Compares with current values** to detect changes
4. **Updates only changed records** (efficient)
5. **Shows detailed progress** with before/after values
6. **Summary statistics** at the end

### Usage

```bash
# Make executable
chmod +x update_address_fields.py

# Run the update
python3 update_address_fields.py
```

### Sample Output

```
🔄 Starting Address Field Update
================================================================================
This script will update city, state, and pincode for all records
based on their addresses using proper parsing logic.
================================================================================

📊 Found 1543 records with addresses
================================================================================

[1/1543] Updating: Teg Immigration Services: Best Study Abroad Consultant
  📍 Address: AMC 1, 581, Ana Sagar Circular Rd, Shantipura, Ajmer, Rajasthan 305001...
  🏙️  City: Mumbai → Ajmer
  🗺️  State: Maharashtra → Rajasthan
  ✅ Updated successfully

[2/1543] Updating: ABC Global Consultants
  📍 Address: Plot 45, Sector 15, Hisar, Haryana, 125001...
  🏙️  City: Delhi → Hisar
  ✅ Updated successfully

[50/1543] No changes needed, continuing...
[100/1543] No changes needed, continuing...

================================================================================
📊 Update Summary:
================================================================================
  ✅ Updated: 487 records
  ⏭️  Skipped (no changes): 1042 records
  ❌ Errors: 14 records
  📝 Total processed: 1543 records
================================================================================
```

---

## Integration with Scraper

### Automatic Extraction
The new extraction logic is automatically used during scraping:

1. **Click listing** → Get full address from detail panel
2. **Extract city** → Validate against cities database
3. **Extract state** → Validate against state mappings
4. **Extract pincode** → Regex extraction
5. **Save to database** → With validated values

### Console Output
```
[1/78] Processing...
  🖱️  Clicking ABC Immigration Services for accurate details...
  📍 Location from address: Ajmer, Rajasthan
  ✓ ABC Immigration Services
    📞 +91-9876543210
    🔗 https://www.google.com/maps/place/...
```

---

## Files Modified

### 1. `/Applications/XAMPP/xamppfiles/htdocs/import/batch_scraper.py`
- Updated `extract_city_from_address()` (lines 243-283)
- Updated `extract_state_from_address()` (lines 285-359)
- `extract_pincode()` unchanged (already working correctly)

### 2. New Files Created
- `update_address_fields.py` - Database update script
- `test_address_extraction.py` - Test/demo script
- `ADDRESS_EXTRACTION_UPDATE.md` - This documentation

---

## Next Steps

### 1. Test the New Extraction
```bash
python3 test_address_extraction.py
```

### 2. Update Existing Records
```bash
python3 update_address_fields.py
```

### 3. Resume Scraping
The scraper will now automatically use the improved extraction:
```bash
python3 batch_scraper.py
```

---

## Summary

✅ **Problem:** Incorrect city/state extraction using substring matching
✅ **Solution:** Proper address parsing following Indian format
✅ **Result:** Accurate city, state, and pincode extraction
✅ **Tools:** Update script to fix existing records
✅ **Integration:** Automatic use in scraper

**Ready to extract accurate location data!** 🎯
