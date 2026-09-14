"""Robust Tesla careers adapter for the current official Tesla jobs feed."""

from __future__ import annotations

import re

import job_scraper as js

TESLA_CAREERS_URL = "https://www.tesla.com/careers"
TESLA_STATE_URL = "https://www.tesla.com/cua-api/apps/careers/state"


def _job_slug(title: str) -> str:
    """Create the slug format used by Tesla's current job-detail URLs."""
    return re.sub(r"[^a-z0-9]+", "-", str(title or "").casefold()).strip("-")


def tesla_job_url(title: str, job_id: str) -> str:
    slug = _job_slug(title)
    return f"https://www.tesla.com/careers/search/job/{slug}-{job_id}"


def iter_tesla_postings(data):
    """Yield job dictionaries regardless of which list Tesla nests them in.

    Tesla's feed is a large nested state object. Older code only recognized a
    list when its *first* element looked like a job. The live feed can mix
    objects, so discover each job dictionary directly instead.
    """
    seen: set[str] = set()
    for obj in js._walk_json(data):
        if not isinstance(obj, dict) or not {"id", "t", "l"}.issubset(obj):
            continue
        job_id = str(obj.get("id", "")).strip()
        title = str(obj.get("t", "")).strip()
        if not job_id or not title or job_id in seen:
            continue
        seen.add(job_id)
        yield obj


def scrape_tesla(url: str, company: str, official_url: str | None = None) -> None:
    """Scrape active Tesla roles from Tesla's first-party careers state feed."""
    try:
        data = js._request(TESLA_STATE_URL).json()
        lookup = data.get("lookup") if isinstance(data, dict) else {}
        lookup = lookup if isinstance(lookup, dict) else {}
        locations = lookup.get("locations", {})
        locations = locations if isinstance(locations, dict) else {}
        home = js._normalize_official_url(official_url, TESLA_CAREERS_URL)

        found = 0
        for job in iter_tesla_postings(data):
            job_id = str(job.get("id", "")).strip()
            title = str(job.get("t", "")).strip()
            location = str(locations.get(str(job.get("l", "")), "N/A"))
            if js.add_result(
                company,
                title,
                location,
                tesla_job_url(title, job_id),
                "N/A",
                home,
            ):
                found += 1

        if found == 0:
            # This is diagnostic, not a failure: it can also mean every matching
            # active Tesla role is already in seen_links.csv.
            print("Tesla official feed: 0 unseen matching U.S. roles")
        else:
            print(f"Tesla official feed: {found} unseen matching U.S. roles")
    except Exception as exc:
        js.log_error(company, f"Tesla official API: {exc}")


def install() -> None:
    """Replace the legacy Tesla parser before job_scraper.main() runs."""
    js.scrape_tesla = scrape_tesla
