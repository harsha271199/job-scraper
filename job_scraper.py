"""
Job scraper for Harshavardhan Kagithoju.

Sources:
- Direct company career pages/APIs when practical (Apple, Google, Tesla, etc.)
- ATS APIs (Greenhouse, Lever, Ashby, Workday) as reliable backends
- Every result can also carry the company's official careers homepage

Runs hourly in GitHub Actions and sends Telegram alerts.
"""

from __future__ import annotations

import json
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ─── SETTINGS ─────────────────────────────────────────────────────────────────

LOCAL_TZ = ZoneInfo("America/Phoenix")
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/152.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT = 15

# Only roles relevant to a Data Science / software / cloud search.
ROLE_KEYWORDS = [
    # Data Engineering
    "data engineer",
    "analytics engineer",
    "data infrastructure",
    "big data engineer",
    "etl engineer",
    "pipeline engineer",
    # Data Science
    "data scientist",
    "applied scientist",
    "quantitative analyst",
    "research scientist",
    # AI / ML
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "mlops",
    "llmops",
    "llm engineer",
    "generative ai",
    "nlp engineer",
    "applied ml",
    "ai platform",
    # Software Engineering
    "software engineer",
    "software developer",
    "sde",
    "swe",
    "backend engineer",
    "platform engineer",
    # Cloud / Infra
    "cloud engineer",
    "devops engineer",
    "site reliability",
    "sre",
    # Analytics / BI
    "data analyst",
    "business analyst",
    "business intelligence",
    "bi engineer",
    "bi analyst",
    "product analyst",
    "growth analyst",
    "reporting analyst",
]

LEVEL_KEYWORDS = [
    # Intern / co-op
    "intern",
    "internship",
    "co-op",
    "coop",
    "co op",
    "fall 2026",
    "winter 2027",
    "spring 2027",
    "summer 2027",
    # New grad / entry level
    "new grad",
    "new graduate",
    "entry level",
    "entry-level",
    "associate",
    "junior",
    "early career",
    "early careers",
    "0-2 years",
    "1-2 years",
    "1-3 years",
    "2-3 years",
    "recent graduate",
    # Mid-level
    "mid level",
    "mid-level",
    "software engineer i",
    "software engineer ii",
    "engineer i",
    "engineer ii",
    "analyst i",
    "analyst ii",
    "scientist i",
    "scientist ii",
    "level 2",
    "level 3",
    "level 4",
    "l2",
    "l3",
    "l4",
]

NO_KEYWORDS = [
    # Seniority
    "senior",
    " sr.",
    " sr ",
    "staff engineer",
    "principal",
    "director",
    "manager",
    "lead",
    "vp ",
    "vice president",
    "head of",
    "chief",
    "distinguished",
    "fellow",
    "software engineer iii",
    "engineer iii",
    "engineer iv",
    "level 5",
    "level 6",
    "l5",
    "l6",
    # Wrong tech domains
    "c++",
    "embedded",
    "firmware",
    "hardware engineer",
    "fpga",
    "asic",
    "rf engineer",
    "mechanical",
    "civil",
    "electrical engineer",
    "manufacturing",
    # Non-tech
    "sales",
    "marketing",
    "account executive",
    "account manager",
    "recruiter",
    "talent acquisition",
    "hr ",
    "human resources",
    "legal",
    "accounting",
    "finance analyst",
    "controller",
    "nurse",
    "doctor",
    "physician",
    "clinical",
    "ux designer",
    "ui designer",
    "graphic designer",
    "copywriter",
    "content writer",
    "social media",
    "customer success",
    "customer support",
    "customer service",
    "supply chain",
    "logistics",
    "procurement",
    "paint",
    "cnc",
    "material handler",
    "technician",
    # Clearance-heavy
    "clearance required",
    "secret clearance",
    "ts/sci",
    "top secret",
    "dod ",
    "defense contractor",
]

US_STATE_NAMES = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
]
US_ABBRS = [
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
    "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
    "wi", "wy", "dc",
]
US_CITY_HINTS = [
    "tempe", "phoenix", "scottsdale", "cupertino", "sunnyvale", "mountain view",
    "san jose", "san francisco", "san mateo", "palo alto", "seattle", "bellevue",
    "new york city", "new york", "austin", "chicago", "boston", "los angeles",
    "denver", "atlanta", "dallas", "houston", "redmond", "irvine", "fremont",
    "greater seattle area", "space coast",
]
FOREIGN_MARKERS = [
    "canada", "united kingdom", " uk", "india", "germany", "france", "ireland",
    "poland", "australia", "singapore", "japan", "korea", "netherlands",
    "spain", "italy", "sweden", "switzerland", "mexico", "brazil", "taiwan",
    "israel", "china", "austria", "belgium", "denmark", "finland", "norway",
    "portugal", "romania", "new zealand",
]

GOOGLE_SEARCH_TERMS = [
    "software engineer",
    "data engineer",
    "data scientist",
    "machine learning engineer",
    "cloud engineer",
    "business analyst",
]


# ─── STATE / LOGGING ──────────────────────────────────────────────────────────

results: list[dict] = []
old_links: set[str] = set()
error_messages: list[str] = []
_state_lock = threading.Lock()


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def log_error(company: str, message: str) -> None:
    message = str(message)
    if len(message) > 300:
        message = message[:300] + "..."
    with _state_lock:
        error_messages.append(f"[ERROR] {company}: {message}")


# ─── FILTERING ────────────────────────────────────────────────────────────────

def keyword_match(title: str) -> bool:
    """Return True for target early/mid-career data/software/cloud roles."""
    t = (title or "").lower().strip()
    if not t:
        return False

    if any(nk in t for nk in NO_KEYWORDS):
        return False

    if not any(rk in t for rk in ROLE_KEYWORDS):
        return False

    if any(lk in t for lk in LEVEL_KEYWORDS):
        return True

    seniority_signals = [
        "senior", "staff", "principal", "director", "lead", "manager",
        "head", "vp", "chief", "sr.", " sr ",
    ]
    return not any(s in t for s in seniority_signals)


def is_us_location(location: str | None) -> bool:
    """
    Conservative U.S. location test.

    Plain "Remote" no longer automatically counts as U.S. This prevents
    listings such as "Remote, United Kingdom" and "Remote - Canada" from
    passing the U.S. filter.
    """
    if not location:
        return False

    loc = re.sub(r"\s+", " ", str(location)).strip().lower()
    if not loc or loc in {"n/a", "na", "unknown", "various"}:
        return False

    explicit_us = (
        "united states" in loc
        or "united states of america" in loc
        or " usa" in f" {loc}"
        or bool(re.search(r"\b(?:u\.?s\.?a?|us)\b", loc))
        or any(state in loc for state in US_STATE_NAMES)
        or any(city in loc for city in US_CITY_HINTS)
        or any(re.search(rf"(?:,\s*|\b){abbr}\b", loc) for abbr in US_ABBRS)
    )
    if explicit_us:
        return True

    if any(marker in loc for marker in FOREIGN_MARKERS):
        return False

    if "remote" in loc:
        return False

    return False


def _normalize_official_url(official_url: str | None, fallback: str) -> str:
    official = (official_url or "").strip()
    return official if official and official.lower() != "nan" else fallback


def add_result(
    company: str,
    title: str,
    location: str,
    link: str,
    posted: str = "N/A",
    official_url: str | None = None,
    assume_us: bool = False,
) -> bool:
    """Filter, de-dupe and add one result. Thread-safe."""
    title = re.sub(r"\s+", " ", str(title or "")).strip()
    location = re.sub(r"\s+", " ", str(location or "N/A")).strip()
    link = str(link or "").strip()

    if not link or not keyword_match(title):
        return False
    if not assume_us and not is_us_location(location):
        return False

    with _state_lock:
        if link in old_links:
            return False
        old_links.add(link)
        results.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "link": link,
                "posted": posted or "N/A",
                "official_url": _normalize_official_url(official_url, link),
            }
        )
    return True


# ─── COMMON HTML / JSON HELPERS ───────────────────────────────────────────────

def _request(url: str, *, params: dict | None = None) -> requests.Response:
    response = requests.get(
        url,
        params=params,
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response


def _extract_posted(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    match = re.search(
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},\s+20\d{2}\b",
        text,
        flags=re.I,
    )
    return match.group(0) if match else "N/A"


def _extract_location_from_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()

    match = re.search(
        r"\bLocation\s+(.+?)(?=\s+(?:Actions|Role Number|Weekly Hours|Submit|Share)\b|$)",
        text,
        flags=re.I,
    )
    if match:
        return match.group(1).strip(" -|")

    state_pattern = "|".join(re.escape(a.upper()) for a in US_ABBRS)
    match = re.search(
        rf"\b([A-Z][A-Za-z .'\-]+,\s*(?:{state_pattern})(?:,\s*USA)?)\b",
        text,
    )
    if match:
        return match.group(1).strip()

    for city in US_CITY_HINTS:
        if city in text.lower():
            match = re.search(re.escape(city), text, flags=re.I)
            return match.group(0) if match else city.title()

    return "N/A"


def _json_location(value) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [_json_location(v) for v in value]
        return "; ".join(p for p in parts if p and p != "N/A") or "N/A"
    if isinstance(value, dict):
        address = value.get("address")
        if isinstance(address, dict):
            parts = [
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]
            rendered = ", ".join(str(p) for p in parts if p)
            if rendered:
                return rendered
        for key in (
            "location", "locations", "name", "locationName", "city",
            "formattedAddress", "displayName",
        ):
            if key in value and value[key]:
                rendered = _json_location(value[key])
                if rendered != "N/A":
                    return rendered
    return "N/A"


def _walk_json(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_json(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_json(value)


def _looks_like_job_url(url: str, source_url: str) -> bool:
    if not url:
        return False
    absolute = urljoin(source_url, url)
    parsed = urlparse(absolute)
    source_host = urlparse(source_url).netloc.lower().removeprefix("www.")
    host = parsed.netloc.lower().removeprefix("www.")

    if source_host and not (
        host == source_host
        or host.endswith("." + source_host)
        or source_host.endswith("." + host)
    ):
        return False

    path = parsed.path.lower()
    return any(
        token in path
        for token in (
            "/details/",
            "/jobs/",
            "/job/",
            "/careers/search/job/",
            "/applications/jobs/results/",
            "/positions/",
            "/open-positions/",
        )
    )


def _candidate_from_json(
    obj: dict, source_url: str, company: str
) -> tuple[str, str, str, str] | None:
    raw_type = obj.get("@type")
    is_jobposting = (
        raw_type == "JobPosting"
        or (isinstance(raw_type, list) and "JobPosting" in raw_type)
    )

    title = ""
    for key in ("title", "jobTitle", "name", "t"):
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            title = val.strip()
            break

    if not title or not keyword_match(title):
        return None

    location = "N/A"
    for key in (
        "jobLocation", "locations", "location", "locationName",
        "formattedLocation", "l",
    ):
        if obj.get(key) is not None:
            location = _json_location(obj.get(key))
            if location != "N/A":
                break

    link = ""
    for key in (
        "url", "jobUrl", "jobURL", "canonicalUrl", "applyUrl",
        "externalUrl", "detailUrl", "absolute_url",
    ):
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            candidate = urljoin(source_url, val.strip())
            if _looks_like_job_url(candidate, source_url) or is_jobposting:
                link = candidate
                break

    if not link and company.casefold() == "google":
        for key in ("id", "jobId", "job_id"):
            value = obj.get(key)
            if value is not None and re.fullmatch(r"\d{10,}", str(value)):
                slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
                link = (
                    "https://www.google.com/about/careers/applications/jobs/results/"
                    f"{value}-{slug}"
                )
                break

    if not link:
        return None

    posted = "N/A"
    for key in ("datePosted", "posted", "postedDate", "publishDate", "publishedAt"):
        val = obj.get(key)
        if val:
            posted = str(val)
            break

    return title, location, link, posted


def scrape_official_html(
    url: str,
    company: str,
    official_url: str | None = None,
    *,
    params: dict | None = None,
    assume_us: bool = False,
) -> int:
    """Scrape job links/data from an official company careers HTML page."""
    count_before = len(results)
    response = _request(url, params=params)
    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    home = _normalize_official_url(official_url, final_url)

    for script in soup.find_all("script"):
        script_type = (script.get("type") or "").lower()
        raw = script.string or script.get_text()
        raw = (raw or "").strip()
        if not raw:
            continue

        should_try = (
            script_type == "application/ld+json"
            or raw.startswith("{")
            or raw.startswith("[")
        )
        if not should_try or len(raw) > 8_000_000:
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        for obj in _walk_json(data):
            candidate = _candidate_from_json(obj, final_url, company)
            if not candidate:
                continue
            title, location, link, posted = candidate
            add_result(
                company,
                title,
                location,
                link,
                posted,
                home,
                assume_us=assume_us,
            )

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        absolute = urljoin(final_url, href)
        if not _looks_like_job_url(absolute, final_url):
            continue

        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
        if not keyword_match(title):
            parent = a.find_parent(["article", "li", "section", "div"])
            if parent:
                heading = parent.find(["h2", "h3", "h4"])
                if heading:
                    title = re.sub(
                        r"\s+", " ", heading.get_text(" ", strip=True)
                    ).strip()
        if not keyword_match(title):
            continue

        parent = a.find_parent(["article", "li", "section", "div"])
        card_text = parent.get_text(" ", strip=True) if parent else ""
        location = _extract_location_from_text(card_text)
        posted = _extract_posted(card_text)

        add_result(
            company,
            title,
            location,
            absolute,
            posted,
            home,
            assume_us=assume_us,
        )

    return len(results) - count_before


# ─── ATS SCRAPERS ─────────────────────────────────────────────────────────────

def scrape_greenhouse(
    url: str, company: str, official_url: str | None = None
) -> None:
    try:
        match = re.search(r"(?:greenhouse\.io|greenhouse\.com)/([^/?\s]+)", url)
        if not match:
            log_error(company, "Bad Greenhouse URL")
            return
        org = match.group(1)
        r = _request(f"https://boards-api.greenhouse.io/v1/boards/{org}/jobs")
        for job in r.json().get("jobs", []):
            add_result(
                company,
                job.get("title", ""),
                job.get("location", {}).get("name", "N/A"),
                job.get("absolute_url", ""),
                job.get("first_published", "N/A"),
                official_url,
            )
    except Exception as exc:
        log_error(company, f"Greenhouse: {exc}")


def scrape_lever(url: str, company: str, official_url: str | None = None) -> None:
    try:
        match = re.search(r"lever\.co/([^/?\s]+)", url)
        if not match:
            log_error(company, "Bad Lever URL")
            return
        org = match.group(1)
        r = _request(f"https://api.lever.co/v0/postings/{org}?mode=json")
        for job in r.json():
            created = job.get("createdAt")
            posted = (
                datetime.utcfromtimestamp(created / 1000).strftime("%Y-%m-%d %H:%M")
                if created
                else "N/A"
            )
            add_result(
                company,
                job.get("text", ""),
                job.get("categories", {}).get("location", "N/A"),
                job.get("hostedUrl", ""),
                posted,
                official_url,
            )
    except Exception as exc:
        log_error(company, f"Lever: {exc}")


def scrape_ashby(url: str, company: str, official_url: str | None = None) -> None:
    try:
        match = re.search(r"ashbyhq\.com/([\w\-]+)", url)
        if not match:
            log_error(company, "Bad Ashby URL")
            return
        org = match.group(1)
        r = _request(f"https://api.ashbyhq.com/posting-api/job-board/{org}")
        for job in r.json().get("jobs", []):
            add_result(
                company,
                job.get("title", ""),
                job.get("location", "N/A"),
                job.get("jobUrl", ""),
                job.get("publishedAt", "N/A"),
                official_url,
            )
    except Exception as exc:
        log_error(company, f"Ashby: {exc}")


def scrape_workday(url: str, company: str, official_url: str | None = None) -> None:
    try:
        match = re.search(
            r"https://([\w\-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[\w\-]+/)?([\w\-]+)",
            url,
        )
        if not match:
            log_error(company, "Bad Workday URL")
            return

        sub, wd, site = match.group(1), match.group(2), match.group(3)
        api = f"https://{sub}.{wd}.myworkdayjobs.com/wday/cxs/{sub}/{site}/jobs"
        headers = {
            **REQUEST_HEADERS,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        offset = 0
        page_size = 20
        max_pages = 5

        for _ in range(max_pages):
            time.sleep(random.uniform(0.25, 0.65))
            r = requests.post(
                api,
                json={
                    "appliedFacets": {},
                    "limit": page_size,
                    "offset": offset,
                    "searchText": "",
                },
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            if r.status_code != 200:
                log_error(company, f"Workday HTTP {r.status_code}")
                break

            data = r.json()
            postings = data.get("jobPostings", [])
            if not postings:
                break

            for job in postings:
                path = job.get("externalPath", "")
                link = f"https://{sub}.{wd}.myworkdayjobs.com/en-US/{site}{path}"
                add_result(
                    company,
                    job.get("title", ""),
                    job.get("locationsText", "N/A"),
                    link,
                    job.get("postedOn", "N/A"),
                    official_url,
                )

            offset += page_size
            if offset >= data.get("total", 0):
                break
    except Exception as exc:
        log_error(company, f"Workday: {exc}")


# ─── DIRECT OFFICIAL COMPANY SOURCES ─────────────────────────────────────────

def scrape_tesla(url: str, company: str, official_url: str | None = None) -> None:
    """Use the data behind Tesla's official careers search."""
    try:
        data = _request("https://www.tesla.com/cua-api/apps/careers/state").json()
        lookup = data.get("lookup", {})
        locations = {str(k): v for k, v in lookup.get("locations", {}).items()}

        posting_lists = []
        for obj in _walk_json(data):
            for value in obj.values():
                if (
                    isinstance(value, list)
                    and value
                    and isinstance(value[0], dict)
                    and {"id", "t", "l"}.issubset(value[0].keys())
                ):
                    posting_lists.append(value)

        seen_ids: set[str] = set()
        for postings in posting_lists:
            for job in postings:
                job_id = str(job.get("id", "")).strip()
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                location = locations.get(str(job.get("l", "")), "N/A")
                link = f"https://www.tesla.com/careers/search/job/{job_id}"
                add_result(
                    company,
                    job.get("t", ""),
                    location,
                    link,
                    "N/A",
                    _normalize_official_url(
                        official_url, "https://www.tesla.com/careers/search"
                    ),
                )
    except Exception as exc:
        log_error(company, f"Tesla official API: {exc}")


def scrape_apple(url: str, company: str, official_url: str | None = None) -> None:
    """Apple's official U.S. search is server-rendered; scan newest pages."""
    try:
        base = "https://jobs.apple.com/en-us/search"
        total_before = len(results)
        for page in range(1, 6):
            params = {"location": "united-states-USA"}
            if page > 1:
                params["page"] = page
            scrape_official_html(
                base,
                company,
                official_url or "https://jobs.apple.com/en-us/search",
                params=params,
                assume_us=True,
            )
        if len(results) == total_before:
            log_error(company, "Apple official pages returned no matching roles")
    except Exception as exc:
        log_error(company, f"Apple official page: {exc}")


def scrape_google(url: str, company: str, official_url: str | None = None) -> None:
    """Search several role families on Google's official Careers site."""
    base = "https://www.google.com/about/careers/applications/jobs/results/"
    try:
        total_before = len(results)
        for term in GOOGLE_SEARCH_TERMS:
            scrape_official_html(
                base,
                company,
                official_url or base,
                params={"q": term, "location": "United States"},
            )
        if len(results) == total_before:
            log_error(company, "Google official pages returned no matching roles")
    except Exception as exc:
        log_error(company, f"Google official page: {exc}")


def scrape_official(url: str, company: str, official_url: str | None = None) -> None:
    try:
        scrape_official_html(url, company, official_url or url)
    except Exception as exc:
        log_error(company, f"Official careers page: {exc}")


# ─── DISPATCH / COMPANY CONFIG ────────────────────────────────────────────────

def scrape_company(row) -> None:
    platform = str(row.get("platform", "")).lower().strip()
    url = str(row.get("careers_url", "")).strip()
    company = str(row.get("company", "")).strip()

    raw_official = row.get("official_url", "")
    official_url = "" if pd.isna(raw_official) else str(raw_official).strip()
    official_url = official_url or url

    dispatch = {
        "greenhouse": scrape_greenhouse,
        "lever": scrape_lever,
        "ashby": scrape_ashby,
        "workday": scrape_workday,
        "official": scrape_official,
        "apple": scrape_apple,
        "google": scrape_google,
        "tesla": scrape_tesla,
    }

    fn = dispatch.get(platform)
    if not fn:
        log_error(company, f"Unsupported platform: {platform}")
        return

    fn(url, company, official_url)


def load_companies() -> pd.DataFrame:
    """
    Load the large existing ATS list, then apply clean overrides/additions from
    official_companies.csv. An override with the same company name replaces the
    old row.
    """
    base = pd.read_csv("companies.csv")
    if "official_url" not in base.columns:
        base["official_url"] = ""

    override_path = Path("official_companies.csv")
    if not override_path.exists():
        return base

    overrides = pd.read_csv(override_path)
    if "official_url" not in overrides.columns:
        overrides["official_url"] = overrides["careers_url"]

    override_names = set(overrides["company"].astype(str).str.casefold())
    base = base[
        ~base["company"].astype(str).str.casefold().isin(override_names)
    ]
    return pd.concat([base, overrides], ignore_index=True)


# ─── MARKDOWN OUTPUT ──────────────────────────────────────────────────────────

def get_daily_filename() -> str:
    now = now_local()
    return f"{now.day}-{now.strftime('%B')}-Jobs-List.md"


def _strip_repeated_headers(content: str) -> str:
    """Remove duplicate page headers created by older hourly runs."""
    cleaned = []
    for line in content.splitlines():
        if line.startswith("# 📢 Job Listings for Harsha"):
            continue
        if line.startswith("> Updated every hour."):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).lstrip()


def update_daily_markdown(new_jobs: list[dict]) -> None:
    if not new_jobs:
        print("No new jobs found this batch.")
        return

    daily_file = get_daily_filename()
    batch_time = now_local().strftime("%Y-%m-%d %H:%M:%S %Z")

    company_counts: dict[str, int] = {}
    for job in new_jobs:
        company_counts[job["company"]] = company_counts.get(job["company"], 0) + 1

    summary = f"\n📊 **{len(new_jobs)} new jobs this batch:**\n"
    for company, count in sorted(company_counts.items()):
        summary += f"- {company}: {count} job{'s' if count != 1 else ''}\n"

    table = (
        "| 🏢 Company | 📍 Location | 💼 Role | 🔗 Apply | 🏠 Official Careers | 📅 Posted |\n"
        "|---|---|---|---|---|---|\n"
    )
    for job in sorted(new_jobs, key=lambda j: (j["company"].lower(), j["title"].lower())):
        official = job.get("official_url") or job["link"]
        table += (
            f"| **{job['company']}** | {job['location']} | {job['title']} | "
            f"[Apply]({job['link']}) | [Careers]({official}) | {job['posted']} |\n"
        )

    batch_block = f"### 🕐 Batch at {batch_time}\n{summary}\n{table}\n---\n"

    existing = ""
    if Path(daily_file).exists():
        existing = _strip_repeated_headers(
            Path(daily_file).read_text(encoding="utf-8")
        )

    today_str = now_local().strftime("%B %d, %Y")
    header = (
        f"# 📢 Job Listings for Harsha — {today_str}\n"
        "> Updated every hour. Newest batch first. Times shown in America/Phoenix.\n\n"
    )

    body = header + batch_block
    if existing:
        body += "\n" + existing.rstrip() + "\n"

    Path(daily_file).write_text(body, encoding="utf-8")
    Path("README.md").write_text(body, encoding="utf-8")
    print(f"✅ {len(new_jobs)} new jobs written to {daily_file} and README.md")


# ─── TELEGRAM ─────────────────────────────────────────────────────────────────

def _telegram_safe(text: str) -> str:
    return str(text).replace("[", "(").replace("]", ")").replace("*", "")


def send_telegram(new_jobs: list[dict], bot_token: str, chat_id: str) -> None:
    if not new_jobs:
        return

    interns = [
        job
        for job in new_jobs
        if any(
            token in job["title"].lower()
            for token in ("intern", "internship", "co-op", "coop", "co op")
        )
    ]
    fulltime = [job for job in new_jobs if job not in interns]

    msg = (
        f"🚀 *{len(new_jobs)} NEW JOBS — {now_local().strftime('%b %d %H:%M %Z')}*\n"
        f"📋 {len(interns)} Internships | {len(fulltime)} Full-time\n\n"
    )

    def append_jobs(items: list[dict], heading: str) -> None:
        nonlocal msg
        if not items:
            return
        msg += heading + "\n"
        for job in items[:8]:
            company = _telegram_safe(job["company"])
            title = _telegram_safe(job["title"])
            location = _telegram_safe(job["location"])
            msg += (
                f"\n🏢 *{company}*\n"
                f"💼 {title}\n"
                f"📍 {location}\n"
                f"🔗 [Apply]({job['link']})\n"
            )
            official = job.get("official_url", "")
            if official and urlparse(official).netloc != urlparse(job["link"]).netloc:
                msg += f"🏠 [Official careers]({official})\n"

    append_jobs(interns, "━━━ 🎓 INTERNSHIPS / CO-OPS ━━━")
    append_jobs(fulltime, "\n━━━ 💼 FULL-TIME ━━━")

    total_shown = min(len(interns), 8) + min(len(fulltime), 8)
    if len(new_jobs) > total_shown:
        msg += (
            f"\n[👉 View all {len(new_jobs)} jobs on GitHub]"
            "(https://github.com/harsha271199/job-scraper#readme)"
        )

    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        requests.post(
            endpoint,
            json={
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=REQUEST_TIMEOUT,
        ).raise_for_status()
        print(f"📱 Telegram sent: {len(new_jobs)} jobs")
    except Exception as exc:
        print(f"Telegram error: {exc}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main() -> None:
    global old_links

    old_path = Path("seen_links.csv")
    if old_path.exists():
        try:
            old_df = pd.read_csv(old_path)
            old_links = set(old_df["link"].dropna().astype(str).unique())
        except Exception as exc:
            print(f"Could not read seen_links.csv: {exc}")
            old_links = set()

    companies_df = load_companies()
    print(f"Scraping {len(companies_df)} companies...")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(scrape_company, row)
            for _, row in companies_df.iterrows()
        ]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                log_error("worker", exc)

    print(f"Found {len(results)} new jobs")
    update_daily_markdown(results)

    if results:
        new_df = pd.DataFrame(results)
        new_df[["link"]].to_csv(
            old_path,
            mode="a",
            index=False,
            header=not old_path.exists(),
        )

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if bot_token and chat_id:
        send_telegram(results, bot_token, chat_id)
    else:
        print("No Telegram credentials — skipping notification")

    if error_messages:
        print("\n--- ERRORS ---")
        for error in error_messages[:25]:
            print(error)


if __name__ == "__main__":
    main()
