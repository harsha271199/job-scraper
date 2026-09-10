"""Adapters for company career sites that do not use the core ATS scrapers."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlparse

import pandas as pd
from bs4 import BeautifulSoup

import job_scraper as js


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_snap_jobs(html: str, base_url: str = "https://careers.snap.com/jobs"):
    """Yield jobs from Snap's official server-rendered careers table."""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()

    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(base_url, anchor.get("href", ""))
        parsed = urlparse(absolute)
        query = parse_qs(parsed.query)

        if parsed.netloc.lower() != "careers.snap.com":
            continue
        if parsed.path.rstrip("/") != "/job" or not query.get("id"):
            continue

        title = _clean(anchor.get_text(" ", strip=True))
        if not title or absolute in seen:
            continue

        row = anchor.find_parent("tr")
        cells = []
        if row:
            cells = [_clean(c.get_text(" ", strip=True)) for c in row.find_all(["td", "th"])]

        location = cells[-1] if len(cells) >= 2 else "N/A"
        job_type = cells[-2] if len(cells) >= 3 else "N/A"
        team = cells[-3] if len(cells) >= 4 else "N/A"

        seen.add(absolute)
        yield {
            "title": title,
            "location": location,
            "job_type": job_type,
            "team": team,
            "link": absolute,
        }


def scrape_snap(url: str, company: str, official_url: str | None = None) -> None:
    """Scrape Snap directly from careers.snap.com; no ATS API required."""
    try:
        response = js._request(url)
        home = official_url or "https://careers.snap.com/jobs"
        for job in parse_snap_jobs(response.text, response.url):
            js.add_result(
                company,
                job["title"],
                job["location"],
                job["link"],
                "N/A",
                home,
            )
    except Exception as exc:
        js.log_error(company, f"Snap official careers: {exc}")


def install() -> None:
    """Extend job_scraper.scrape_company with proprietary official sources."""
    original = js.scrape_company

    def scrape_company_with_official_adapters(row) -> None:
        platform = str(row.get("platform", "")).lower().strip()
        if platform != "snap":
            original(row)
            return

        company = str(row.get("company", "")).strip()
        url = str(row.get("careers_url", "")).strip()
        raw_official = row.get("official_url", "")
        official_url = "" if pd.isna(raw_official) else str(raw_official).strip()
        scrape_snap(url, company, official_url or url)

    js.scrape_company = scrape_company_with_official_adapters
