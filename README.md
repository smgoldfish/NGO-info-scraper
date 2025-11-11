# NGO Scraper – Wikipedia for NGOs (Prototype)

> **Part of a larger project**: Building a **searchable, Wikipedia-style directory of NGOs** to help donors, researchers, and volunteers discover credible organizations easily.

---

## Project Goal
Create a **structured, searchable database of NGOs** by scraping key information from their official websites:
- NGO name
- Year founded
- Field(s) of work
- Operational areas
- Contact info
- Website URL

All data saved in clean **JSON format**.

---

## Repository Purpose
This repo tracks **iterative development** of the web scraper.  
Each version (`v1/`, `v2/`, etc.) contains:
- The full Python script
- Sample output (`.json`)
- A `notes.md` file explaining:
  - What approach was tried
  - What worked
  - What failed (and why)
  - Lessons learned

This helps us **learn from failures**, avoid repeating mistakes, and build a robust final scraper.

---

## Folder Structure
repo/
├── README.md               # Overview of the repo, setup instructions, and how to use the versioning system
├── versions/               # Main directory for tracking code iterations
│   ├── v1/                 # Folder for version 1 (name sequentially like v1, v2, etc.)
│   │   ├── script.py       # The code file for this version (copy the full script here)
│   │   ├── output.json     # Output/results from running this version (e.g., scraped data or logs)
│   │   └── notes.md        # Markdown file with details: approach used, what worked, what was wrong/fixed, and any learnings
│   ├── v2/                 # Folder for version 2
│   │   ├── script.py
│   │   ├── output.json
│   │   └── notes.md
│   ├── v3/                 # And so on for each new version...
│   │   ├── script.py
│   │   ├── output.json
│   │   └── notes.md
│   └── ...                 # Add new subfolders as you iterate
└── utils/                  # Optional: Shared utilities or helpers that don't change per version (e.g., common functions or requirements.txt)
