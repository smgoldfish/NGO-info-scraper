# v1 – Sub-page Crawling + JavaScript Rendering

## Approach
The v1 scraper is designed to work on **real-world NGO sites** that hide data on sub-pages or load it with JavaScript.

**Core workflow**

1. **Main page fetch** – `requests` (or Selenium with `--use-browser` for JS-heavy sites).  
2. **Sub-page discovery** – Scan `<a>` tags for keywords (`about`, `history`, `our story`, `contact`, …) in **link text *or* href**.  
3. **Recursive extraction** – Run the same field-extractors on the discovered sub-page(s).  
4. **Field extraction**  
   * **Name** – `<title>` → `<h1>` fallback.  
   * **Year founded** – Regex patterns (`founded in 1994`, `since 1994`, …) + parent-section scan.  
   * **Fields of work** – Look for keyword sections → `<li>` list; fallback to a static keyword list.  
   * **Operational areas** – Keyword sections → `<li>`; fallback to a hard-coded country list.  
   * **Contact** – `mailto:` / `tel:` links + regex for email, phone, address.  
5. **Custom selector persistence** – Interactive prompt saves a CSS selector per domain in `custom_selectors.json`.  
6. **Politeness** – `time.sleep(1)` between sub-page requests.

**Goal:** Reduce manual selector entry while handling the most common NGO site patterns.

---

## Insights & Fixes

### What Excelled
| Site | Success |
|------|----------|
| **nazindia.org** | Auto-navigated to “Our History” sub-page, extracted **fields of work** (`Care And Support Services`, `Young People’s Initiative`, `lgbtqia+ initiative`) and **operational area** (`India`). |
| **aaina.org.in** | Detected **phone** (`0674-2360630`) and **operational areas** (`Asia`, `India`). |
| **All sites** | NGO name correctly pulled from `<title>` / `<h1>`. |

### What Failed (and why)

| Site | Missing / Wrong | Root cause |
|------|----------------|------------|
| **nazindia.org** | `year_founded = null` | Year appears **inside a JS-loaded div** (`#ourHistory > div > …`) that is **not** inside a “founded/since” text block. Regex never fires. |
| **nazindia.org** | `contact_info.address = "1994 to date"` | Address regex mistakenly captured the year phrase. |
| **akanksha.org** | `year_founded = null` | No “founded” text; year is buried in a **timeline graphic** (image) or a **React component**. |
| **akanksha.org** | `fields_of_work = ["About Us", "Key Programs"]` | Heuristic grabbed navigation items, not actual program list. |
| **akanksha.org** | `contact_info.address` = long marketing blurb | Regex matched a sentence that contains numbers + street-like words. |
| **aaina.org.in** | `fields_of_work` = **huge list of navigation items** | The keyword “Our Work” is used for the **menu**, not a program list. |
| **All sites** | `operational_areas` often empty or incomplete | Only hard-coded country names are recognized; many NGOs list **states** or **city names**. |

### Fixes & Next Steps (v2 roadmap)

| # | Improvement | Implementation hint |
|---|-------------|---------------------|
| 1 | **Parse `schema.org` / JSON-LD** | `soup.find('script', type='application/ld+json')` → extract `foundingDate`, `areaServed`, `contactPoint`. |
| 2 | **Robust year detection** | After regex, scan **all numeric 4-digit strings** in the page and keep the first one that appears near “founded/established/start”. |
| 3 | **Better address filter** | Require **at least one street suffix** (`Road`, `Marg`, `Nagar`, `St`, `Ave`) **and** a postal code pattern. |
| 4 | **Program-list heuristics** | Look for `<ul>`/`<ol>` with **≥3 items** under a heading that contains *program*, *initiative*, *project* (ignore nav menus). |
| 5 | **Replace Selenium with Playwright** | Faster headless browser, built-in auto-wait, less resource-heavy. |
| 6 | **PDF fallback** | If a link ends in `.pdf` and contains “annual report”/“history”, download + `PyPDF2`/`pdfplumber` text extraction. |
| 7 | **Configurable country/state list** | Load from a JSON file; allow fuzzy match for city names. |
| 8 | **Batch mode + progress bar** | `tqdm`, parallel `concurrent.futures.ThreadPoolExecutor`. |

