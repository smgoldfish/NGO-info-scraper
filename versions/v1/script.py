import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse, urljoin
import os
import argparse
from datetime import datetime

# File for storing custom selectors
CUSTOM_FILE = 'custom_selectors.json'

def load_custom_selectors():
    """Load custom selectors from JSON file if it exists."""
    if os.path.exists(CUSTOM_FILE):
        try:
            with open(CUSTOM_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Invalid custom selectors file. Starting fresh.")
            return {}
    return {}

def save_custom_selectors(customs):
    """Save custom selectors to JSON file."""
    with open(CUSTOM_FILE, 'w') as f:
        json.dump(customs, f, indent=4)

def fetch_page(url):
    """Fetch the webpage content and return BeautifulSoup object."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        else:
            print(f"Failed to fetch {url}: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def find_and_fetch_subpage(main_soup, base_url, keywords):
    """Find a link matching keywords and fetch the subpage."""
    for a in main_soup.find_all('a', href=True):
        text = a.text.strip().lower()
        if any(k.lower() in text for k in keywords):
            href = a['href']
            sub_url = urljoin(base_url, href)
            print(f"Found potential subpage: {sub_url}")
            return fetch_page(sub_url), sub_url
    return None, None

def extract_ngo_name(soup, custom_selector=None):
    """Extract NGO name using custom selector or defaults."""
    if custom_selector:
        elem = soup.select_one(custom_selector)
        if elem:
            return elem.text.strip()
    
    # Default: Title or h1
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find('h1')
    if h1:
        return h1.text.strip()
    return None

def extract_year_founded(soup, custom_selector=None):
    """Extract year founded using custom selector or keyword patterns."""
    if custom_selector:
        elem = soup.select_one(custom_selector)
        if elem:
            text = elem.text
        else:
            text = ''
    else:
        text = soup.get_text()
    
    # Regex patterns for year
    patterns = [
        r'(?:founded|established|started)\s*(?:in|on)?\s*(\d{4})',
        r'year\s*(?:founded|established):\s*(\d{4})',
        r'since\s*(\d{4})'
    ]
    current_year = datetime.now().year
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= current_year:
                return str(year)
    
    # Alternative: Look in 'About Us' section
    about_sections = soup.find_all(text=re.compile(r'(about\s*us|our\s*story|history)', re.IGNORECASE))
    for section in about_sections:
        parent = section.find_parent(['div', 'section', 'p'])
        if parent:
            matches = re.findall(r'\d{4}', parent.text)
            for m in matches:
                year = int(m)
                if 1900 <= year <= current_year:
                    return str(year)
    return None

def extract_fields_of_work(soup, custom_selector=None):
    """Extract fields of work using custom selector or heuristics."""
    if custom_selector:
        elems = soup.select(custom_selector)
        if elems:
            return [elem.text.strip() for elem in elems if elem.text.strip()]
    
    # Heuristics: Find sections with keywords and lists
    keywords = ['fields of work', 'areas of focus', 'our work', 'programs', 'initiatives', 'what we do']
    for keyword in keywords:
        section = soup.find(text=re.compile(keyword, re.IGNORECASE))
        if section:
            parent = section.find_parent(['div', 'section'])
            if parent:
                lis = parent.find_all('li')
                if lis:
                    return [li.text.strip() for li in lis if li.text.strip()]
    # Fallback: Common fields if mentioned
    text = soup.get_text().lower()
    common_fields = ['education', 'health', 'environment', 'poverty alleviation', 'women empowerment', 'child welfare', 'human rights', 'disaster relief', 'animal welfare']
    found = [field for field in common_fields if field in text]
    return found if found else []

def extract_operational_areas(soup, custom_selector=None):
    """Extract operational areas using custom selector or heuristics."""
    if custom_selector:
        elems = soup.select(custom_selector)
        if elems:
            return [elem.text.strip() for elem in elems if elem.text.strip()]
    
    # Heuristics: Find sections with keywords like 'where we work'
    keywords = ['operational areas', 'where we work', 'locations', 'countries', 'regions', 'our reach']
    for keyword in keywords:
        section = soup.find(text=re.compile(keyword, re.IGNORECASE))
        if section:
            parent = section.find_parent(['div', 'section'])
            if parent:
                lis = parent.find_all('li')
                if lis:
                    return [li.text.strip() for li in lis if li.text.strip()]
    # Fallback: Look for country/region names (expanded list)
    text = soup.get_text()
    # Regex for common countries/regions (non-exhaustive)
    country_pattern = r'\b(India|United States|USA|UK|Canada|Australia|Africa|Asia|Europe|Latin America|Middle East|Brazil|China|France|Germany|Japan|Mexico|Nigeria|South Africa|Kenya|Ethiopia|Uganda)\b'
    countries = re.findall(country_pattern, text, re.IGNORECASE)
    return list(set(countries)) if countries else []

def extract_contact_info(soup, custom_selector=None):
    """Extract contact info using custom selector or patterns."""
    contact = {}
    if custom_selector:
        elem = soup.select_one(custom_selector)
        if elem:
            text = elem.text
        else:
            text = ''
    else:
        text = soup.get_text()
    
    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.[\w]+', text)
    if email_match:
        contact['email'] = email_match.group(0)
    
    # Phone
    phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}', text)  # More flexible
    if phone_match:
        contact['phone'] = phone_match.group(0)
    
    # Address: More general heuristic
    address_match = re.search(r'\d{1,5}\s+[\w\s]+(?:street|st|avenue|ave|road|rd|blvd|boulevard|lane|ln|marg|path|way)?\b.*?(?:,\s*[\w\s]+(?:\d{5})?)?', text, re.IGNORECASE | re.DOTALL)
    if address_match:
        contact['address'] = address_match.group(0).strip().replace('\n', ' ')
    
    # Alternative: Look in 'Contact Us' section or links
    if not contact:
        contact_sections = soup.find_all(text=re.compile(r'contact\s*us|get in touch', re.IGNORECASE))
        for section in contact_sections:
            parent = section.find_parent(['div', 'section', 'footer'])
            if parent:
                # Find mailto/tel links
                for a in parent.find_all('a', href=True):
                    if 'mailto:' in a['href']:
                        contact['email'] = a['href'].replace('mailto:', '')
                    if 'tel:' in a['href']:
                        contact['phone'] = a['href'].replace('tel:', '')
                # Fallback regex on parent text
                parent_text = parent.get_text()
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.[\w]+', parent_text)
                if email_match:
                    contact['email'] = email_match.group(0)
                phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}', parent_text)
                if phone_match:
                    contact['phone'] = phone_match.group(0)
    
    return contact if contact else None

def parse_page(main_soup, url, customs):
    """Parse the page(s) to extract all required information, fetching subpages if needed."""
    domain = urlparse(url).netloc
    custom = customs.get(domain, {})
    
    # Initial extraction from main page
    data = {
        'ngo_name': extract_ngo_name(main_soup, custom.get('ngo_name')),
        'year_founded': extract_year_founded(main_soup, custom.get('year_founded')),
        'fields_of_work': extract_fields_of_work(main_soup, custom.get('fields_of_work')),
        'operational_areas': extract_operational_areas(main_soup, custom.get('operational_areas')),
        'contact_info': extract_contact_info(main_soup, custom.get('contact_info')),
        'website_url': url
    }
    
    # Check for missing fields (excluding always-present URL)
    missing = [k for k, v in data.items() if not v and k != 'website_url']
    if not missing:
        return data
    
    print(f"Initial missing info for {url}: {missing}")
    
    # Fetch about-like subpage if relevant fields missing
    about_fields = ['year_founded', 'fields_of_work', 'operational_areas']
    if any(f in missing for f in about_fields):
        about_keywords = ['about', 'about us', 'our story', 'history', 'who we are', 'mission']
        about_soup, _ = find_and_fetch_subpage(main_soup, url, about_keywords)
        if about_soup:
            for field in about_fields:
                if field in missing:
                    if field == 'year_founded':
                        val = extract_year_founded(about_soup, custom.get(field))
                    elif field == 'fields_of_work':
                        val = extract_fields_of_work(about_soup, custom.get(field))
                    elif field == 'operational_areas':
                        val = extract_operational_areas(about_soup, custom.get(field))
                    if val:
                        data[field] = val
                        missing.remove(field)
    
    # Fetch contact subpage if still missing
    if 'contact_info' in missing:
        contact_keywords = ['contact', 'contact us', 'get in touch', 'reach us']
        contact_soup, _ = find_and_fetch_subpage(main_soup, url, contact_keywords)
        if contact_soup:
            val = extract_contact_info(contact_soup, custom.get('contact_info'))
            if val:
                data['contact_info'] = val
                missing.remove('contact_info')
    
    return data

def save_to_json(data, filename):
    """Save extracted data to JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Data saved to {filename}")

def handle_feedback(soup, url, data, customs, no_feedback=False):
    """Handle user feedback for missing information and retry."""
    missing = [k for k, v in data.items() if not v and k != 'website_url']
    if not missing or no_feedback:
        return data
    
    print(f"Still missing info for {url} after subpages: {missing}")
    while True:
        resp = input("Do you want to provide feedback for corrections? (y/n): ").strip().lower()
        if resp != 'y':
            break
        
        field = input(f"Which field to correct? ({', '.join(missing)}): ").strip()
        if field not in data:
            print("Invalid field.")
            continue
        
        selector = input("Provide a new CSS selector (e.g., 'div.about > p'): ").strip()
        
        # Map field to extract function
        extract_map = {
            'ngo_name': extract_ngo_name,
            'year_founded': extract_year_founded,
            'fields_of_work': extract_fields_of_work,
            'operational_areas': extract_operational_areas,
            'contact_info': extract_contact_info
        }
        
        if field in extract_map:
            new_val = extract_map[field](soup, selector)
            if new_val:
                print(f"Found with new selector: {new_val}")
                update = input("Update and save this selector? (y/n): ").strip().lower()
                if update == 'y':
                    domain = urlparse(url).netloc
                    if domain not in customs:
                        customs[domain] = {}
                    customs[domain][field] = selector
                    save_custom_selectors(customs)
                    data[field] = new_val
                    if field in missing:
                        missing.remove(field)
            else:
                print("No information found with the provided selector.")
    
    return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape key information from NGO websites.")
    parser.add_argument('urls', nargs='+', help="URLs of NGO websites to scrape")
    parser.add_argument('--no-feedback', action='store_true', help="Run without interactive feedback")
    args = parser.parse_args()
    
    customs = load_custom_selectors()
    
    for url in args.urls:
        main_soup = fetch_page(url)
        if not main_soup:
            continue
        
        data = parse_page(main_soup, url, customs)
        data = handle_feedback(main_soup, url, data, customs, args.no_feedback)
        
        domain = urlparse(url).netloc.replace('www.', '')
        filename = f"{domain}.json"
        save_to_json(data, filename)
