"""Fetch all registered municipal source pages, cache full text in knowledge/_sources_cache/,
and generate knowledge/_FETCH_LOG.md with main-content word counts.

Usage:
    python -m rag.sync_sources_cache
"""
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import Dict, Any, List, Set, Tuple
from html.parser import HTMLParser
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
CACHE_DIR = KNOWLEDGE_DIR / "_sources_cache"
FETCH_LOG_PATH = KNOWLEDGE_DIR / "_FETCH_LOG.md"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

REGISTERED_URLS = [
    ("complaint_pmc_gov_in_home", "https://complaint.pmc.gov.in/home"),
    ("mahadiscom_in_home", "https://www.mahadiscom.in/en/home/"),
    ("mahapolice_gov_in", "https://www.mahapolice.gov.in"),
    ("rtionline_gov_in_guidelines", "https://rtionline.gov.in/guidelines.php"),
    ("rtionline_gov_in_faq", "https://rtionline.gov.in/faq.php"),
    ("rtionline_maharashtra_gov_in_index", "https://rtionline.maharashtra.gov.in/index.php"),
    ("mpcb_gov_in_contact_us", "https://mpcb.gov.in/contact-us"),
    ("ndma_gov_in", "https://ndma.gov.in/"),
    ("ndma_gov_in_contact_us", "https://ndma.gov.in/en/contact-us"),
    ("ndma_gov_in_urban_flood", "https://ndma.gov.in/en/urban-flood"),
    ("ndma_gov_in_heatwave", "https://ndma.gov.in/en/heatwave"),
    ("ndma_gov_in_fire_safety", "https://ndma.gov.in/en/fire-safety"),
    ("cpcb_nic_in_national_air_quality_index", "https://cpcb.nic.in/national-air-quality-index/"),
    ("ncvbdc_mohfw_gov_in", "https://ncvbdc.mohfw.gov.in/"),
    ("pib_gov_in_prid_1745433", "https://pib.gov.in/PressReleasePage.aspx?PRID=1745433"),
    ("pune_gov_in_right_to_service_act", "https://pune.gov.in/document/right-to-service-act/"),
    ("wii_gov_in_noise_pollution", "https://wii.gov.in/noise_pollution"),
]


class CleanTextExtractor(HTMLParser):
    """Extract readable text from HTML, skipping scripts, styles, and hidden state fields."""
    def __init__(self):
        super().__init__()
        self.text_lines: List[str] = []
        self.in_skip_tag = False
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]):
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg"):
            self.in_skip_tag = True
        elif tag_lower == "title":
            self.in_title = True
        elif tag_lower in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br"):
            # Add line boundary
            if self.text_lines and self.text_lines[-1] != "":
                self.text_lines.append("")

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg"):
            self.in_skip_tag = False
        elif tag_lower == "title":
            self.in_title = False
        elif tag_lower in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            if self.text_lines and self.text_lines[-1] != "":
                self.text_lines.append("")

    def handle_data(self, data: str):
        if self.in_title:
            self.title += " " + data.strip()
        if not self.in_skip_tag:
            cleaned = data.strip()
            # Skip viewstate or long base64 lines
            if len(cleaned) > 200 and (" " not in cleaned and "/" in cleaned):
                return
            if cleaned:
                self.text_lines.append(cleaned)


def fetch_url(url: str) -> Tuple[int, str, str]:
    """Fetch URL and return (status_code, title, clean_text)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        extractor = CleanTextExtractor()
        extractor.feed(r.text)
        clean_text = "\n".join(extractor.text_lines)
        title = extractor.title.strip() or url
        return r.status_code, title, clean_text
    except Exception as e:
        print(f"[FETCH ERROR] {url}: {e}")
        return 0, "", ""


def sync_all_sources():
    """Download all registered URLs and save to CACHE_DIR."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    cached_pages: Dict[str, Dict[str, Any]] = {}

    for slug, url in REGISTERED_URLS:
        cache_file = CACHE_DIR / f"{slug}.md"
        status, title, body = fetch_url(url)

        if status != 200 or not body.strip():
            # If fetch failed, check if previous cache exists
            if cache_file.exists():
                print(f"[CACHE] Using existing cache for {slug} ({url})")
            else:
                print(f"[FAIL] Could not fetch or cache {slug} ({url})")
                continue

        content = (
            f"---\n"
            f'url: "{url}"\n'
            f'slug: "{slug}"\n'
            f'fetched_at: "{today}"\n'
            f"http_status: {status}\n"
            f'title: "{title}"\n'
            f"---\n\n"
            f"{body}\n"
        )
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[CACHED] {slug}.md ({len(body.split())} words, status {status})")

    # Now read all cached files and compute boilerplate frequency
    files = list(CACHE_DIR.glob("*.md"))
    file_lines: Dict[Path, List[str]] = {}
    line_file_count: Counter = Counter()

    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            text = fh.read()
        # Separate frontmatter
        if text.startswith("---"):
            parts = text.split("---", 2)
            body = parts[2] if len(parts) >= 3 else text
        else:
            body = text

        lines = [line.strip() for line in body.splitlines() if line.strip()]
        file_lines[f] = lines
        unique_lines = set(lines)
        for uline in unique_lines:
            line_file_count[uline] += 1

    # Boilerplate lines are those appearing in >= 3 cached files
    boilerplate: Set[str] = {line for line, count in line_file_count.items() if count >= 3}
    print(f"\n[BOILERPLATE] Identified {len(boilerplate)} recurring boilerplate lines across cached files.")

    # Generate _FETCH_LOG.md
    log_rows: List[Dict[str, Any]] = []

    for f in sorted(files):
        with open(f, "r", encoding="utf-8") as fh:
            raw = fh.read()

        url = ""
        status = "0"
        date_str = today
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            fm = parts[1]
            body = parts[2]
            for l in fm.splitlines():
                if ":" in l:
                    k, v = l.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip().strip('"').strip("'")
                    if k == "url":
                        url = v
                    elif k == "http_status":
                        status = v
                    elif k == "fetched_at":
                        date_str = v
        else:
            body = raw

        lines = [line.strip() for line in body.splitlines() if line.strip()]
        total_words = sum(len(l.split()) for l in lines)
        main_lines = [l for l in lines if l not in boilerplate]
        main_words = sum(len(l.split()) for l in main_lines)

        index_shell_urls = {
            "https://wii.gov.in/noise_pollution",
            "https://pune.gov.in/document/right-to-service-act/",
        }

        if url in index_shell_urls:
            valid = False
            note = "index page, not a content source"
        elif status == "200" and main_words >= 150:
            valid = True
            note = "Valid source"
        elif status == "200":
            valid = False
            note = "Fewer than 150 main-content words"
        else:
            valid = False
            note = "Fetch failed"

        log_rows.append({
            "date": date_str,
            "url": url,
            "status": status,
            "total_words": total_words,
            "main_words": main_words,
            "valid": valid,
            "note": note,
            "file": f.name,
        })

    # Write _FETCH_LOG.md
    lines_out = [
        "# Knowledge Base Official Source Fetch Log",
        "",
        "This file is generated automatically from `knowledge/_sources_cache/` by `python -m rag.sync_sources_cache`.",
        "DO NOT hand-edit this file.",
        "",
        "| Date | URL | HTTP Status | Total Words | Main Words | Status / Notes |",
        "|---|---|---|---|---|---|",
    ]

    for r in log_rows:
        lines_out.append(
            f"| {r['date']} | {r['url']} | {r['status']} | {r['total_words']} | {r['main_words']} | {r['note']} |"
        )

    lines_out.append("")
    with open(FETCH_LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")

    print(f"\n[SUCCESS] Generated {FETCH_LOG_PATH} with {len(log_rows)} tracked sources.")


if __name__ == "__main__":
    sync_all_sources()
