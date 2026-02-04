# Random Query Mode

## What Changed

The scraper now uses **random query selection** for each city instead of processing all cities for one query before moving to the next.

---

## Old Behavior (Sequential by Query)

```
Query: immigration consultant
  ├─ Andhra Pradesh
  │   ├─ Adoni (immigration consultant)
  │   ├─ Amalapuram (immigration consultant)
  │   ├─ Anakapalle (immigration consultant)
  │   └─ ... (all 82 cities)
  ├─ Rajasthan
  │   ├─ Ajmer (immigration consultant)
  │   └─ ... (all 73 cities)
  └─ ... (all 33 states, all 1,202 cities)

Query: visa consultant
  ├─ Andhra Pradesh
  │   ├─ Adoni (visa consultant)
  │   └─ ... (all 82 cities)
  └─ ... (repeat for all states)

... (repeat for all 6 queries)
```

**Total:** 1,202 cities × 6 queries = 7,212 searches
**Order:** All cities for query 1, then all cities for query 2, etc.

---

## New Behavior (Random Query per City)

```
Andhra Pradesh
  ├─ Adoni → 🎲 Random: "IELTS coaching"
  ├─ Amalapuram → 🎲 Random: "immigration consultant"
  ├─ Anakapalle → 🎲 Random: "study abroad consultant"
  ├─ Anantapur → 🎲 Random: "PTE coaching"
  └─ ... (each city gets a random query)

Rajasthan
  ├─ Ajmer → 🎲 Random: "visa consultant"
  ├─ Alwar → 🎲 Random: "overseas education consultant"
  └─ ... (each city gets a random query)

... (continue for all states)
```

**Total:** Still 1,202 cities (but only 1 query per city)
**Order:** Iterate through cities, pick random query for each

---

## Benefits

### 1. More Human-Like Behavior
- ✅ Looks natural (real person would search different things)
- ✅ Less predictable pattern
- ✅ Reduces risk of bot detection
- ✅ Varies the search behavior

### 2. Diverse Data Quickly
- ✅ Get results for all query types early on
- ✅ Don't have to wait for 1,202 cities before seeing other queries
- ✅ Better data distribution across queries

### 3. Faster Coverage
- ✅ Only scrapes each city once
- ✅ Completes in 1,202 searches instead of 7,212
- ✅ **6x faster** to complete all cities

---

## Console Output

You'll now see:

```
============================================================
📍 STATE: Andhra Pradesh (82 cities)
============================================================

🎲 Random query selected: IELTS coaching

============================================================
🔍 Searching: IELTS coaching in Adoni
============================================================
  🌐 Establishing session with Google...
  🔍 Searching: IELTS coaching at coordinates (15.6261, 77.2724)
  ...

⏳ Waiting 87 seconds before next search...

🎲 Random query selected: immigration consultant

============================================================
🔍 Searching: immigration consultant in Amalapuram
============================================================
  🌐 Establishing session with Google...
  🔍 Searching: immigration consultant at coordinates (16.5777, 82.0033)
  ...
```

The key indicator: **🎲 Random query selected: {query}**

---

## Query Distribution

With random selection, over 1,202 cities you'll get approximately:

- **immigration consultant**: ~200 cities (1/6 of 1,202)
- **visa consultant**: ~200 cities
- **IELTS coaching**: ~200 cities
- **PTE coaching**: ~200 cities
- **study abroad consultant**: ~200 cities
- **overseas education consultant**: ~200 cities

**Note:** Distribution is random, so actual numbers will vary slightly.

---

## Database Impact

Each city will appear in the database **once** (or a few times if there are duplicates from different businesses), but with different `services` based on the random query used.

Before:
```sql
-- Same city, same query, multiple businesses
business_name: ABC Immigration, city: Adoni, services: immigration consultant
business_name: XYZ Immigration, city: Adoni, services: immigration consultant
business_name: DEF Immigration, city: Adoni, services: immigration consultant
```

Now:
```sql
-- Different cities, different random queries
business_name: ABC Immigration, city: Adoni, services: IELTS coaching
business_name: XYZ Consultants, city: Amalapuram, services: immigration consultant
business_name: DEF Academy, city: Anakapalle, services: study abroad consultant
```

---

## Progress Tracking

The scraper still tracks progress by:
- `last_state_index`: Current state position
- `last_city_index`: Current city position
- `last_query_index`: Last query used (for reference, but now random)

Progress is saved after each city, so you can stop/resume anytime.

---

## If You Want to Change It Back

If you prefer to go back to the old behavior (all cities for each query):

1. The old code is commented in the Git history
2. Or I can quickly restore the sequential query loop structure

Just let me know!

---

## What If I Want All Queries for Each City?

If you want to scrape **all 6 queries** for each city (instead of just 1 random query):

- Total searches: 1,202 × 6 = 7,212
- Time: Much longer (6x more searches)
- Benefit: Complete data for each city

This is **Option 3** from earlier. Let me know if you prefer this instead.

---

## Current Configuration

- **Mode**: Random query per city
- **Queries**: 6 available queries
- **Selection**: `random.choice(queries)` on each city
- **Probability**: Each query has equal 1/6 chance

---

## Summary

🎲 **Random query mode activated!**

- Each city gets one random query
- More human-like behavior
- Diverse data distribution
- 6x faster completion (1,202 searches instead of 7,212)
- Still collects comprehensive data across all query types

Ready to start scraping with randomized queries! 🚀
