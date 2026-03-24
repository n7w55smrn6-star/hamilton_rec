import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_PATH = Path(__file__).parent / "data" / "programs.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-CA,en;q=0.9",
}

# Program category pages on hamilton.ca that contain human-readable schedule tables
PROGRAM_PAGES = {
    "Drop-In Gym": "https://www.hamilton.ca/things-do/recreation/programs/drop-programs/drop-gym",
    "Drop-In Swim": "https://www.hamilton.ca/things-do/recreation/programs/drop-programs/drop-swim",
    "Drop-In Skate": "https://www.hamilton.ca/things-do/recreation/programs/drop-programs/drop-skate",
    "Drop-In Waterfit": "https://www.hamilton.ca/things-do/recreation/programs/drop-programs/drop-waterfit",
    "Drop-In Aquafit": "https://www.hamilton.ca/things-do/recreation/programs/drop-programs/drop-aquafit",
    "Registered Programs": "https://www.hamilton.ca/things-do/recreation/programs/registered-programs",
}

# Individual recreation centre pages that list schedules per facility
CENTRE_PAGES = {
    "Ancaster Rotary Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/ancaster-rotary-centre",
    "Bernie Morelli Recreation Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/bernie-morelli-recreation-centre",
    "Central Memorial Recreation Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/central-memorial-recreation-centre",
    "Flamborough Centennial Arena & Community Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/flamborough-centennial-arena-community-centre",
    "Huntington Park Recreation Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/huntington-park-recreation-centre",
    "Kanétskare Recreation Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/kanetskare-recreation-centre",
    "Lisgar Arena & Community Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/lisgar-arena-community-centre",
    "Norman Pinky Lewis Recreation Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/norman-pinky-lewis-recreation-centre",
    "Sir Winston Churchill Recreation Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/sir-winston-churchill-recreation-centre",
    "Valley Park Community Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/valley-park-community-centre",
    "Westmount Recreation Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/westmount-recreation-centre",
    "Winona Community Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/winona-community-centre",
    "YMCA Bob Carter Family Recreation Centre": "https://www.hamilton.ca/things-do/recreation/locations/recreation-centres-indoor-pools/ymca-bob-carter-family-recreation-centre",
}

# Days of week we look for when parsing free-text schedules
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
        "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

TIME_RE = re.compile(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*[-–to]+\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b", re.I)
DAY_RE   = re.compile(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", re.I)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch(url: str, retries: int = 3) -> BeautifulSoup | None:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt + 1, retries, url, exc)
            time.sleep(2 ** attempt)
    log.error("Gave up on %s", url)
    return None


def parse_schedule_text(text: str) -> list[dict]:
    """
    Given a block of text like 'Monday 9:00am - 11:00am, Wednesday 1pm-3pm'
    return a list of {day, start, end} dicts.
    """
    entries = []
    # Split on common delimiters to get day+time segments
    segments = re.split(r"[,;|\n]", text)
    for seg in segments:
        seg = seg.strip()
        day_match = DAY_RE.search(seg)
        time_match = TIME_RE.search(seg)
        if day_match and time_match:
            entries.append({
                "day": day_match.group(0).capitalize(),
                "start": time_match.group(1).strip().lower(),
                "end": time_match.group(2).strip().lower(),
            })
    return entries


def extract_programs_from_page(soup: BeautifulSoup, category: str, centre: str = "") -> list[dict]:
    """
    Try to pull program rows out of whatever table/list structure is on the page.
    Falls back to scanning paragraphs for day+time patterns.
    """
    programs = []

    # --- Strategy 1: Look for HTML tables ---
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        rows = table.find_all("tr")
        for row in rows[1:]:  # skip header row
            cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
            if not cells:
                continue
            program = {
                "category": category,
                "centre": centre,
                "name": "",
                "day": "",
                "start": "",
                "end": "",
                "location": centre,
                "notes": "",
            }
            # Map columns by header name if available
            for i, cell in enumerate(cells):
                if i < len(headers):
                    h = headers[i]
                    if any(k in h for k in ["program", "activity", "name", "class"]):
                        program["name"] = cell
                    elif any(k in h for k in ["day", "date", "time", "schedule", "when"]):
                        times = parse_schedule_text(cell)
                        if times:
                            program["day"]   = times[0]["day"]
                            program["start"] = times[0]["start"]
                            program["end"]   = times[0]["end"]
                        else:
                            program["day"] = cell
                    elif any(k in h for k in ["location", "facility", "centre", "place"]):
                        program["location"] = cell or centre
                    elif any(k in h for k in ["note", "info", "detail", "desc"]):
                        program["notes"] = cell
                else:
                    # No header — guess by content
                    if TIME_RE.search(cell):
                        times = parse_schedule_text(cell)
                        if times:
                            program["day"]   = times[0]["day"]
                            program["start"] = times[0]["start"]
                            program["end"]   = times[0]["end"]
                    elif not program["name"]:
                        program["name"] = cell

            if program["name"] or program["day"]:
                programs.append(program)

    if programs:
        return programs

    # --- Strategy 2: Scan headings + paragraph text ---
    current_program_name = ""
    for tag in soup.find_all(["h2", "h3", "h4", "p", "li", "strong"]):
        text = tag.get_text(" ", strip=True)
        if not text:
            continue

        # Headings often contain program names
        if tag.name in ["h2", "h3", "h4", "strong"] and len(text) < 80:
            current_program_name = text

        # Look for day+time patterns in any element
        times = parse_schedule_text(text)
        if times:
            for t in times:
                programs.append({
                    "category": category,
                    "centre": centre,
                    "name": current_program_name or category,
                    "day": t["day"],
                    "start": t["start"],
                    "end": t["end"],
                    "location": centre,
                    "notes": "",
                })

    return programs


# ---------------------------------------------------------------------------
# Main scraping logic
# ---------------------------------------------------------------------------

def scrape_all() -> list[dict]:
    all_programs: list[dict] = []

    # --- Scrape per-category pages ---
    for category, url in PROGRAM_PAGES.items():
        log.info("Scraping category: %s", category)
        soup = fetch(url)
        if not soup:
            continue
        programs = extract_programs_from_page(soup, category=category)
        log.info("  Found %d entries from %s", len(programs), url)
        all_programs.extend(programs)
        time.sleep(1)  # be polite

    # --- Scrape per-centre pages ---
    for centre_name, url in CENTRE_PAGES.items():
        log.info("Scraping centre: %s", centre_name)
        soup = fetch(url)
        if not soup:
            continue
        programs = extract_programs_from_page(soup, category="Drop-In", centre=centre_name)
        # Deduplicate against what we already have
        existing_keys = {(p["centre"], p["name"], p["day"], p["start"]) for p in all_programs}
        new_entries = [
            p for p in programs
            if (p["centre"], p["name"], p["day"], p["start"]) not in existing_keys
        ]
        log.info("  Found %d new entries from %s", len(new_entries), centre_name)
        all_programs.extend(new_entries)
        time.sleep(1)

    return all_programs


def save(programs: list[dict]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "count": len(programs),
        "programs": programs,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    log.info("Saved %d programs to %s", len(programs), OUTPUT_PATH)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log.info("=== Hamilton Rec Scraper starting ===")
    programs = scrape_all()
    if programs:
        save(programs)
        log.info("Done. %d total programs scraped.", len(programs))
    else:
        log.warning("No programs found — the site may use JavaScript rendering.")
        log.warning("See README.md for instructions on enabling Selenium mode.")
        # Save an empty result so the web UI still loads
        save([])
