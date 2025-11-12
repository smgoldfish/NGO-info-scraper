# versions/v3/script.py
# v3 – India-Specific, Clean Output, Interactive-Aware

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

# Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

CUSTOM_FILE = 'custom_selectors.json'

# Indian states & major cities
INDIAN_STATES = [
    'Delhi', 'Mumbai', 'Pune', 'Bangalore', 'Kolkata', 'Chennai', 'Hyderabad',
    'Ahmedabad', 'Jaipur', 'Lucknow', 'Patna', 'Bhopal', 'Ranchi', 'Guwahati',
    'Odisha', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'Gujarat', 'Rajasthan',
    'Uttar Pradesh', 'Bihar', 'Jharkhand', 'Assam', 'Punjab', 'Haryana',
    'Madhya Pradesh', 'West Bengal', 'Telangana', 'Andhra Pradesh'
]

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

# === FETCH ===
def fetch_page(url, use_playwright=False):
    if use_playwright and PLAYWRIGHT_AVAILABLE:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()
            return BeautifulSoup(html, 'html.parser')
    else:
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            r = requests.get(url, headers=headers, timeout=15)
            return BeautifulSoup(r.text, 'html.parser') if r.status_code == 200 else None
        except:
            return None

# === JSON-LD ===
def extract_from_json_ld(soup):
    data = {}
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            obj = json.loads(script.string)
            items = obj if isinstance(obj, list) else [obj]
            for item in items:
                if item.get('@type') in ['Organization', 'NGO']:
                    if 'foundingDate' in item:
                        data['year_founded'] = item['foundingDate'][:4]
                    if 'name' in item:
                        data['ngo_name'] = item['name']
                    if 'areaServed' in item:
                        areas = item['areaServed']
                        areas = areas if isinstance(areas, list) else [areas]
                        data['operational_areas'] = [a.get('name') for a in areas if a.get('name')]
        except:
            continue
    return data

# === PDF ===
def extract_from_pdf(pdf_url):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
            r = requests.get(pdf_url, timeout=15)
            if r.status_code != 200: return {}
            f.write(r.content)
            path = f.name
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        os.unlink(path)
        m = re.search(r'(?:founded|established|since)\s*(?:in)?\s*(\d{4})', text, re.I)
        return {'year_founded': m.group(1)} if m else {}
    except:
        return {}

# === SUBPAGE & PDF FINDER ===
def find_subpages_and_pdfs(soup, base_url):
    subpages = []
    pdfs = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True).lower()
        full = urljoin(base_url, href)
        if any(k in text or k in href.lower() for k in ['about', 'history', 'contact', 'team', 'state']):
            if full != base_url and '#' not in full:
                subpages.append(full)
        if href.lower().endswith('.pdf') and any(k in text for k in ['report', 'annual']):
            pdfs.append(full)
    return list(set(subpages)), list(set(pdfs))

# === EXTRACTORS ===
def extract_ngo_name(soup, custom=None):
    if custom:
        e = soup.select_one(custom)
        if e: return e.get_text(strip=True)
    return soup.title.string.strip() if soup.title and soup.title.string else None

def extract_year_founded(soup, custom=None):
    if custom:
        e = soup.select_one(custom)
        if e:
            m = re.search(r'\b(19|20)\d{2}\b', e.get_text())
            if m: return m.group(0)
    text = soup.get_text()
    patterns = [
        r'(?:founded|established|since)\s*(?:in)?\s*\b(19|20)\d{2}\b',
        r'\b(19|20)\d{2}\b.*?(?:founded|established)'
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m: return m.group(1) if m.group(1) else m.group(0)
    return None

def extract_fields_of_work(soup, custom=None):
    if custom:
        return [e.get_text(strip=True) for e in soup.select(custom)]
    keywords = ['program', 'initiative', 'project', 'focus', 'work']
    for kw in keywords:
        sec = soup.find(string=re.compile(kw, re.I))
        if sec:
            parent = sec.find_parent(['div', 'section', 'article'])
            if parent:
                ul = parent.find_next(['ul', 'ol'])
                if ul:
                    items = [li.get_text(strip=True) for li in ul.find_all('li')]
                    if len(items) >= 2 and not any('about' in i.lower() for i in items):
                        return items
    return []

def extract_operational_areas(soup, custom=None):
    if custom:
        return [e.get_text(strip=True) for e in soup.select(custom)]
    text = soup.get_text()
    found = []
    for state in INDIAN_STATES:
        if re.search(r'\b' + state + r'\b', text, re.I):
            found.append(state)
    return found

def extract_contact_info(soup, custom=None):
    contact = {}
    text = soup.get_text()

    # Email
    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email:
        contact['email'] = email.group(0)

    # Indian phone patterns
    phone_patterns = [
        r'\+91[\s\-]?\d{10}',
        r'91[\s\-]?\d{10}',
        r'0\d{2,3}[\s\-]?\d{7,8}',
        r'\d{2,3}[\s\-]?\d{7,8}',
        r'P[\s:]*\+?91[\s\-]?\d{10}',
        r'Contact[\s:]*\+?91[\s\-]?\d{10}'
    ]
    for p in phone_patterns:
        m = re.search(p, text)
        if m:
            phone = re.sub(r'[^\d+]', '', m.group(0))
            if len(phone) >= 10:
                contact['phone'] = phone
                break

    # If no phone and dropdown detected
    if 'phone' not in contact:
        if soup.find('select') or soup.find(string=re.compile('select state', re.I)):
            contact['phone'] = 'not found automatically, check manually'

    return contact if contact else None

# === MAIN ===
def parse_ngo(url, use_playwright=False):
    domain = urlparse(url).netloc
    custom = load_custom_selectors().get(domain, {})

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

    # JSON-LD
    data.update(extract_from_json_ld(soup))

    # Main page
    data['ngo_name'] = data['ngo_name'] or extract_ngo_name(soup, custom.get('ngo_name'))
    data['year_founded'] = data['year_founded'] or extract_year_founded(soup, custom.get('year_founded'))
    data['fields_of_work'] = data['fields_of_work'] or extract_fields_of_work(soup, custom.get('fields_of_work'))
    data['operational_areas'] = data['operational_areas'] or extract_operational_areas(soup, custom.get('operational_areas'))
    data['contact_info'] = data['contact_info'] or extract_contact_info(soup, custom.get('contact_info'))

    # Subpages
    subpages, pdfs = find_subpages_and_pdfs(soup, url)
    for sub_url in subpages[:2]:
        time.sleep(1)
        sub_soup = fetch_page(sub_url, use_playwright)
        if sub_soup:
            if not data['year_founded']:
                data['year_founded'] = extract_year_founded(sub_soup)
            if not data['fields_of_work']:
                data['fields_of_work'] = extract_fields_of_work(sub_soup)
            if not data['contact_info'].get('phone'):
                new_c = extract_contact_info(sub_soup)
                if new_c:
                    data['contact_info'].update(new_c)

    # PDF
    for pdf_url in pdfs[:1]:
        pdf_data = extract_from_pdf(pdf_url)
        if pdf_data.get('year_founded') and not data['year_founded']:
            data['year_founded'] = pdf_data['year_founded']

    return data

# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('urls', nargs='+')
    parser.add_argument('--use-playwright', action='store_true')
    args = parser.parse_args()

    if args.use_playwright and not PLAYWRIGHT_AVAILABLE:
        print("Install: pip install playwright && playwright install")
        exit(1)

    for url in args.urls:
        result = parse_ngo(url, args.use_playwright)
        if result:
            domain = urlparse(url).netloc.replace('www.', '')
            os.makedirs("versions/v4", exist_ok=True)
            with open(f"versions/v4/{domain}.json", 'w') as f:
                json.dump(result, f, indent=4)
            print(f"Saved: versions/v4/{domain}.json")
