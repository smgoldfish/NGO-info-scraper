# versions/v3/script.py
# v3 – Playwright + JSON-LD + PDF Intelligence
# Fixes: Year founded, clean fields, JS sites, PDF reports

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse, urljoin
import os
import argparse
import time
import pdfplumber
import tempfile
from datetime import datetime

# Optional: Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# File for custom selectors
CUSTOM_FILE = 'custom_selectors.json'

# Load/save custom selectors
def load_custom_selectors():
    if os.path.exists(CUSTOM_FILE):
        try:
            with open(CUSTOM_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_custom_selectors(customs):
    with open(CUSTOM_FILE, 'w') as f:
        json.dump(customs, f, indent=4)

# === 1. FETCH PAGE (Playwright or Requests) ===
def fetch_page(url, use_playwright=False):
    if use_playwright and PLAYWRIGHT_AVAILABLE:
        print(f"Using Playwright to render {url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()
            return BeautifulSoup(html, 'html.parser')
    else:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
        except:
            pass
        return None

# === 2. JSON-LD PARSING (schema.org) ===
def extract_from_json_ld(soup):
    data = {}
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            json_data = json.loads(script.string)
            # Handle both dict and list
            items = json_data if isinstance(json_data, list) else [json_data]
            for item in items:
                if item.get('@type') in ['NGO', 'Organization', 'Nonprofit']:
                    if 'foundingDate' in item:
                        data['year_founded'] = item['foundingDate'][:4]
                    if 'name' in item:
                        data['ngo_name'] = item['name']
                    if 'areaServed' in item:
                        areas = item['areaServed']
                        if isinstance(areas, list):
                            data['operational_areas'] = [a.get('name', '') for a in areas if a.get('name')]
                        elif isinstance(areas, dict):
                            data['operational_areas'] = [areas.get('name', '')]
                    if 'contactPoint' in item:
                        cp = item['contactPoint']
                        cps = cp if isinstance(cp, list) else [cp]
                        for c in cps:
                            if c.get('@type') == 'ContactPoint':
                                if 'email' in c:
                                    data['contact_email'] = c['email']
                                if 'telephone' in c:
                                    data['contact_phone'] = c['telephone']
        except:
            continue
    return data

# === 3. PDF TEXT EXTRACTION ===
def extract_from_pdf(pdf_url):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            response = requests.get(pdf_url, timeout=15)
            if response.status_code != 200:
                return {}
            tmp.write(response.content)
            tmp_path = tmp.name

        text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        os.unlink(tmp_path)

        # Look for year
        year_match = re.search(r'(?:founded|established|since)\s*(?:in)?\s*(\d{4})', text, re.I)
        if year_match:
            return {'year_founded': year_match.group(1)}
    except:
        pass
    return {}

# === 4. SUBPAGE & PDF DISCOVERY ===
def find_subpages_and_pdfs(soup, base_url):
    subpages = []
    pdfs = []

    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True).lower()
        full_url = urljoin(base_url, href)

        # Subpages
        if any(k in text or k in href.lower() for k in ['about', 'history', 'our story', 'founding', 'contact']):
            if full_url != base_url and '#' not in full_url:
                subpages.append(full_url)

        # PDFs
        if href.lower().endswith('.pdf') and any(k in text for k in ['report', 'history', 'founded', 'annual']):
            pdfs.append(full_url)

    return list(set(subpages)), list(set(pdfs))

# === 5. EXTRACTION FUNCTIONS ===
def extract_ngo_name(soup, custom=None):
    if custom:
        e = soup.select_one(custom)
        if e: return e.get_text(strip=True)
    return soup.title.string.strip() if soup.title else None

def extract_year_founded(soup, custom=None):
    if custom:
        e = soup.select_one(custom)
        if e: 
            m = re.search(r'\b(19|20)\d{2}\b', e.get_text())
            if m: return m.group(0)
    text = soup.get_text()
    patterns = [
        r'(?:founded|established|started|since)\s*(?:in)?\s*(19|20)\d{2}',
        r'\b(19|20)\d{2}\s*(?:founded|established)'
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m: return m.group(1) if m.group(1) else m.group(0)
    return None

def extract_fields_of_work(soup, custom=None):
    if custom:
        elems = soup.select(custom)
        return [e.get_text(strip=True) for e in elems if e.get_text(strip=True)]
    
    # Look for program lists
    keywords = ['program', 'initiative', 'project', 'work', 'focus']
    for kw in keywords:
        sec = soup.find(text=re.compile(kw, re.I))
        if sec:
            parent = sec.find_parent(['div', 'section', 'article'])
            if parent:
                ul = parent.find('ul') or parent.find('ol')
                if ul:
                    items = [li.get_text(strip=True) for li in ul.find_all('li')]
                    if len(items) >= 2:
                        return items
    return []

def extract_operational_areas(soup, custom=None):
    if custom:
        elems = soup.select(custom)
        return [e.get_text(strip=True) for e in elems if e.get_text(strip=True)]
    
    text = soup.get_text()
    countries = re.findall(r'\b(India|Delhi|Mumbai|Pune|Odisha|Maharashtra|Karnataka|Tamil Nadu|USA|UK|Africa|Asia)\b', text, re.I)
    return list(set(countries)) if countries else []

def extract_contact_info(soup, custom=None):
    contact = {}
    text = soup.get_text()
    
    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email: contact['email'] = email.group(0)
    
    phone = re.search(r'[\+]?[\d\s\-\(\)]{10,}', text)
    if phone: contact['phone'] = phone.group(0)
    
    return contact if contact else None

# === 6. MAIN PARSING LOGIC ===
def parse_ngo(url, use_playwright=False, customs=None):
    if customs is None:
        customs = {}
    domain = urlparse(url).netloc
    custom = customs.get(domain, {})

    print(f"\nScraping: {url}")
    soup = fetch_page(url, use_playwright)
    if not soup:
        return None

    data = {
        'ngo_name': None,
        'year_founded': None,
        'fields_of_work': [],
        'operational_areas': [],
        'contact_info': {},
        'website_url': url
    }

    # 1. JSON-LD (highest priority)
    json_data = extract_from_json_ld(soup)
    data.update(json_data)

    # 2. Main page extraction
    data['ngo_name'] = data['ngo_name'] or extract_ngo_name(soup, custom.get('ngo_name'))
    data['year_founded'] = data['year_founded'] or extract_year_founded(soup, custom.get('year_founded'))
    data['fields_of_work'] = data['fields_of_work'] or extract_fields_of_work(soup, custom.get('fields_of_work'))
    data['operational_areas'] = data['operational_areas'] or extract_operational_areas(soup, custom.get('operational_areas'))
    data['contact_info'] = data['contact_info'] or extract_contact_info(soup, custom.get('contact_info'))

    # 3. Subpages
    subpages, pdfs = find_subpages_and_pdfs(soup, url)
    for sub_url in subpages[:2]:  # limit to 2
        time.sleep(1)
        sub_soup = fetch_page(sub_url, use_playwright)
        if sub_soup:
            # Update year
            if not data['year_founded']:
                data['year_founded'] = extract_year_founded(sub_soup, custom.get('year_founded'))
            
            # Update fields of work
            if not data['fields_of_work']:
                data['fields_of_work'] = extract_fields_of_work(sub_soup, custom.get('fields_of_work'))
            
            # Update contact info
            if not data['contact_info'] or not data['contact_info'].get('email'):
                new_contact = extract_contact_info(sub_soup, custom.get('contact_info'))
                if new_contact:
                    data['contact_info'].update(new_contact)

    # 4. PDFs
    for pdf_url in pdfs[:1]:
        time.sleep(1)
        pdf_data = extract_from_pdf(pdf_url)
        if pdf_data.get('year_founded') and not data['year_founded']:
            data['year_founded'] = pdf_data['year_founded']

    return data

# === 7. MAIN ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NGO Scraper v3 – Playwright + JSON-LD + PDF")
    parser.add_argument('urls', nargs='+', help="NGO websites")
    parser.add_argument('--use-playwright', action='store_true', help="Use Playwright for JS sites")
    args = parser.parse_args()

    if args.use_playwright and not PLAYWRIGHT_AVAILABLE:
        print("Playwright not installed. Run: pip install playwright && playwright install")
        exit(1)

    customs = load_custom_selectors()

    for url in args.urls:
        result = parse_ngo(url, args.use_playwright, customs)
        if result:
            domain = urlparse(url).netloc.replace('www.', '')
            filename = f"versions/v3/{domain}.json"
            os.makedirs("versions/v3", exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(result, f, indent=4)
            print(f"Saved: {filename}")
