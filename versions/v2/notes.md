## v2 – Playwright + JSON-LD + PDF Intelligence

## Approach
v3 makes the scraper **smarter and faster** by understanding **how modern websites actually store data**.

### Core Upgrades
1. **Playwright** → Replaces Selenium  
   - Faster, auto-waits for content  
   - Headless Chrome/Firefox  
   - `pip install playwright && playwright install`

2. **JSON-LD Parsing** → Reads `schema.org` data  
   ```html
   <script type="application/ld+json">
   { "foundingDate": "1994", "name": "Naz Foundation" }
   </script>

### New Superpowers (Simple Terms)

| Feature | What It Does | Example Fix |
|--------|--------------|------------|
| **Playwright** | Opens websites **like a real browser**, waits for content to load | nazindia.org → now sees "1994" in JS-loaded div |
| **JSON-LD** | Reads **hidden machine-readable data** in `<script type="application/ld+json">` | Gets `foundingDate: "1994-01-01"` directly |
| **PDF Support** | Downloads and **reads text from PDF reports** | If "Annual Report 2023.pdf" says "Founded in 1994", we get it |

> Think of it like this:  
> **Playwright** = eyes that wait and see everything  
> **JSON-LD** = a secret note the website leaves for robots  
> **PDF** = opening a locked drawer where NGOs keep their real history
