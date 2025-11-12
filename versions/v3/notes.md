# v3 – India-Focused, Clean & Interactive-Aware Scraper

> **Target**: Only **Indian NGOs**  
> **Goal**: Extract **accurate, clean, human-readable data** even from dropdowns, PDFs, and JS-heavy sites

---

## Approach

v3 is **optimized for Indian NGO websites** with real-world quirks:
- Phone numbers in `+91`, `011`, `P:` formats
- State-specific contact via **dropdowns**
- Year hidden in text, JSON, or PDF
- Fields of work buried under "Programs", not nav menus

### Core Upgrades

| Feature | How It Works |
|--------|--------------|
| **India-Only Phone** | Regex for `+91`, `011-`, `P:+91`, etc. |
| **Dropdown Detection** | If `<select>` or "select state" found → `phone: "not found automatically"` |
| **Operational Areas** | Only **Indian states/cities** (list of 30+) — **removes `India`, `Asia`** |
| **Year Founded** | Full `19XX`/`20XX` near "founded", "since", "established" |
| **Fields of Work** | Looks for `<ul>` under "program", "initiative", "project" — **ignores nav menus** |
| **Playwright** | Full JS rendering (dropdowns, lazy-load) |
| **JSON-LD** | Reads `schema.org` for `foundingDate`, `areaServed` |
| **PDF Fallback** | Reads "Annual Report" PDFs for year |

> **Priority Order**: JSON-LD → Page Text → Subpage → PDF

---

## Insights & Fixes (From v2)

### What v2 Got Wrong

| Issue | Example | v2 Output |
|------|--------|----------|
| `year_founded` | `"19"` | Partial match |
| `fields_of_work` | Nav menu items | `"About Us", "Contact"` |
| `phone` | `"\n\n\n"` | Bad regex |
| `operational_areas` | `"India", "Asia"` | Too broad |
| **Pratham dropdown** | State offices | Missed entirely |

### v3 Fixes

| Site | Expected Output |
|------|-----------------|
| **nazindia.org** | `year: "1994"`, clean fields, `phone: "+91..."` |
| **akanksha.org** | `operational_areas: ["Mumbai", "Pune"]` |
| **aaina.org.in** | Clean `fields_of_work`, `phone` fixed |
| **pratham.org** | `phone: "not found automatically, check manually"` |

---

## Expected Output Example (Pratham)

```json
{
  "ngo_name": "Pratham",
  "year_founded": "1994",
  "fields_of_work": ["Early Childhood Education", "Learning Camps", "Vocational Training"],
  "operational_areas": ["Delhi", "Mumbai", "Maharashtra", "Bihar", "Odisha", "Gujarat"],
  "contact_info": {
    "email": "info@pratham.org",
    "phone": "not found automatically, check manually"
  },
  "website_url": "https://pratham.org"
}
