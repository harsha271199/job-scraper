"""Adapters for company career sites that do not use the core ATS scrapers."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlparse

import pandas as pd
from bs4 import BeautifulSoup

import job_scraper as js


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _best_role_string(container) -> str:
    """Find the smallest text fragment in a job card that looks like a target role."""
    candidates = []
    for text in container.stripped_strings:
        cleaned = _clean(text)
        lower = cleaned.lower()
        if any(keyword in lower for keyword in js.ROLE_KEYWORDS):
            candidates.append(cleaned)
    if not candidates:
        return ""
    return min(candidates, key=len)


def _best_us_location_string(container) -> str:
    """Find a concise U.S. location fragment inside a rendered job card."""
    candidates = []
    for text in container.stripped_strings:
        cleaned = _clean(text)
        if len(cleaned) > 180:
            continue
        if js.is_us_location(cleaned):
            candidates.append(cleaned)
    if not candidates:
        return "N/A"
    return min(candidates, key=len)


def _nearest_role_container(anchor, max_depth: int = 7):
    """Walk up from an apply/title link until a compact role-bearing card is found."""
    node = anchor
    for _ in range(max_depth):
        node = getattr(node, "parent", None)
        if node is None:
            break
        if _best_role_string(node):
            return node
    return anchor


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


def parse_kula_jobs(
    html: str,
    base_url: str = "https://careers.kula.ai/10xgenomics",
    board_slug: str = "10xgenomics",
):
    """Yield server-rendered Kula job cards such as 10x Genomics' current board."""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    host = urlparse(base_url).netloc.lower()
    path_re = re.compile(rf"/{re.escape(board_slug)}/\d+/?$")

    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(base_url, anchor.get("href", ""))
        parsed = urlparse(absolute)
        if parsed.netloc.lower() != host or not path_re.search(parsed.path):
            continue
        if absolute in seen:
            continue

        card = _nearest_role_container(anchor)
        title = _best_role_string(card)
        if not title:
            continue
        location = _best_us_location_string(card)

        seen.add(absolute)
        yield {"title": title, "location": location, "link": absolute}


def scrape_kula(url: str, company: str, official_url: str | None = None) -> None:
    """Scrape a Kula-hosted branded careers site without relying on a stale ATS."""
    try:
        response = js._request(url)
        board_slug = urlparse(response.url).path.strip("/").split("/")[0] or "10xgenomics"
        home = official_url or url
        for job in parse_kula_jobs(response.text, response.url, board_slug):
            js.add_result(
                company,
                job["title"],
                job["location"],
                job["link"],
                "N/A",
                home,
            )
    except Exception as exc:
        js.log_error(company, f"Kula official careers: {exc}")


def parse_google_company_jobs(
    html: str,
    base_url: str = "https://www.google.com/about/careers/applications/jobs/results",
):
    """Yield job cards from a Google Careers search result page."""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()

    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(base_url, anchor.get("href", ""))
        parsed = urlparse(absolute)
        host = parsed.netloc.lower().removeprefix("www.")
        if host != "google.com":
            continue
        if "/about/careers/applications/jobs/results/" not in parsed.path:
            continue
        if absolute.rstrip("/") == base_url.rstrip("/") or absolute in seen:
            continue

        card = _nearest_role_container(anchor)
        title = _best_role_string(card)
        if not title:
            title = _clean(anchor.get_text(" ", strip=True))
        if not title:
            continue

        location = _best_us_location_string(card)
        seen.add(absolute)
        yield {"title": title, "location": location, "link": absolute}


def scrape_deepmind(url: str, company: str, official_url: str | None = None) -> None:
    """Search Google Careers directly with the DeepMind organization filter."""
    try:
        base = "https://www.google.com/about/careers/applications/jobs/results"
        home = official_url or "https://deepmind.google/careers/"
        for term in js.GOOGLE_SEARCH_TERMS:
            response = js._request(
                base,
                params={
                    "company": "DeepMind",
                    "q": term,
                    "location": "United States",
                },
            )
            for job in parse_google_company_jobs(response.text, response.url):
                js.add_result(
                    company,
                    job["title"],
                    job["location"],
                    job["link"],
                    "N/A",
                    home,
                )
    except Exception as exc:
        js.log_error(company, f"DeepMind Google Careers: {exc}")


def parse_color_health_jobs(
    html: str,
    base_url: str = "https://www.color.com/careers/",
):
    """Yield Color Health roles linked by its official careers page."""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()

    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(base_url, anchor.get("href", ""))
        parsed = urlparse(absolute)
        if parsed.netloc.lower() != "app.careerpuck.com":
            continue
        if "/job-board/color-health/job/" not in parsed.path or absolute in seen:
            continue

        card = _nearest_role_container(anchor, max_depth=3)
        title = _best_role_string(anchor) or _best_role_string(card)
        location = _best_us_location_string(anchor)
        if location == "N/A":
            location = _best_us_location_string(card)
        if not title:
            continue

        seen.add(absolute)
        yield {"title": title, "location": location, "link": absolute}


def scrape_color_health(url: str, company: str, official_url: str | None = None) -> None:
    """Scrape jobs exposed directly on Color Health's official careers page."""
    try:
        response = js._request(url)
        home = official_url or "https://www.color.com/careers/"
        for job in parse_color_health_jobs(response.text, response.url):
            js.add_result(
                company,
                job["title"],
                job["location"],
                job["link"],
                "N/A",
                home,
            )
    except Exception as exc:
        js.log_error(company, f"Color Health official careers: {exc}")


def install() -> None:
    """Extend job_scraper.scrape_company with proprietary official sources."""
    if getattr(js, "_official_adapters_installed", False):
        return

    original = js.scrape_company
    handlers = {
        "snap": scrape_snap,
        "kula": scrape_kula,
        "deepmind": scrape_deepmind,
        "color_health": scrape_color_health,
    }

    def scrape_company_with_official_adapters(row) -> None:
        platform = str(row.get("platform", "")).lower().strip()
        handler = handlers.get(platform)
        if handler is None:
            original(row)
            return

        company = str(row.get("company", "")).strip()
        url = str(row.get("careers_url", "")).strip()
        raw_official = row.get("official_url", "")
        official_url = "" if pd.isna(raw_official) else str(raw_official).strip()
        handler(url, company, official_url or url)

    js.scrape_company = scrape_company_with_official_adapters
    js._official_adapters_installed = True
