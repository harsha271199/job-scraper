"""One-click resume portal integration for the job scraper.

This module never reads the private master resume. It publishes only derived
job signals (title, location, detected skills, role profile, and the real apply
URL) to job_signals.json, then rewrites outward-facing Apply links to the
browser-only resume portal.
"""

from __future__ import annotations

import copy
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

PORTAL_URL = "https://harsha271199.github.io/job-scraper/"
FEED_PATH = Path("job_signals.json")
INVENTORY_PATH = Path("resume_skill_inventory.json")
REQUEST_TIMEOUT = 12

_SIGNAL_TERMS = (
    "data pipeline", "data pipelines", "etl", "elt", "data warehouse",
    "data lake", "distributed systems", "streaming", "kafka", "api",
    "rest api", "microservices", "cloud", "infrastructure as code", "iac",
    "ci/cd", "observability", "monitoring", "incident response",
    "root cause analysis", "data quality", "data modeling", "schema design",
    "machine learning", "deep learning", "nlp", "llm", "analytics",
    "dashboard", "business intelligence", "sql", "python",
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def job_id(link: str) -> str:
    return hashlib.sha256(str(link).encode("utf-8")).hexdigest()[:16]


def classify_profile(title: str, skills: list[str] | None = None) -> str:
    text = f"{title} {' '.join(skills or [])}".casefold()
    if any(x in text for x in ("data scientist", "machine learning", "ml engineer", "ai engineer", "applied scientist", "nlp", "llm")):
        return "machine-learning"
    if any(x in text for x in ("data engineer", "analytics engineer", "etl engineer", "pipeline engineer", "big data")):
        return "data-engineering"
    if any(x in text for x in ("data analyst", "business analyst", "business intelligence", "bi analyst", "product analyst", "growth analyst", "reporting analyst")):
        return "data-analytics"
    if any(x in text for x in ("cloud engineer", "devops", "site reliability", "sre", "platform engineer")):
        return "cloud-devops"
    if any(x in text for x in ("software engineer", "software developer", "backend engineer", "swe", "sde")):
        return "software-engineering"
    return "general-technical"


def _visible_page_text(url: str) -> str:
    """Fetch readable job text, with a Workday CXS detail fallback."""
    parsed = urlparse(url)
    host = parsed.netloc.casefold()

    if "myworkdayjobs.com" in host:
        match = re.match(r"([^.]+)\.(wd\d+)\.myworkdayjobs\.com", host)
        path_match = re.match(r"/(?:[a-z]{2}-[A-Z]{2}/)?([^/]+)(/job/.*)$", parsed.path)
        if match and path_match:
            tenant = match.group(1)
            wd = match.group(2)
            site = path_match.group(1)
            external_path = path_match.group(2)
            api = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{external_path}"
            r = requests.get(api, headers={**_HEADERS, "Accept": "application/json"}, timeout=REQUEST_TIMEOUT)
            if r.ok:
                data = r.json()
                info = data.get("jobPostingInfo") or {}
                text = " ".join(
                    str(info.get(k) or "")
                    for k in ("jobDescription", "additionalJobDescription", "title", "location")
                )
                if text.strip():
                    return BeautifulSoup(html.unescape(text), "html.parser").get_text(" ", strip=True)

    r = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for bad in soup(["script", "style", "noscript", "svg"]):
        bad.decompose()
    return soup.get_text(" ", strip=True)


def _load_inventory() -> list[dict]:
    try:
        data = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        return [x for x in data.get("skills", []) if isinstance(x, dict) and x.get("name")]
    except Exception:
        return []


def detect_skills(text: str, inventory: list[dict] | None = None, limit: int = 24) -> list[str]:
    inventory = inventory if inventory is not None else _load_inventory()
    haystack = str(text or "")
    ranked: list[tuple[int, str]] = []
    for item in inventory:
        aliases = [str(item.get("name", "")), *[str(a) for a in item.get("aliases", [])]]
        count = 0
        for alias in aliases:
            alias = alias.strip()
            if not alias:
                continue
            pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", re.I)
            count += len(pattern.findall(haystack))
        if count:
            ranked.append((count, str(item["name"])))
    ranked.sort(key=lambda x: (-x[0], x[1].casefold()))
    return [name for _, name in ranked[:limit]]


def detect_signal_terms(text: str, limit: int = 12) -> list[str]:
    low = str(text or "").casefold()
    return [term for term in _SIGNAL_TERMS if term in low][:limit]


def _load_feed() -> dict:
    if not FEED_PATH.exists():
        return {"version": 1, "jobs": {}}
    try:
        data = json.loads(FEED_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), dict):
            raise ValueError("bad feed")
        return data
    except Exception:
        return {"version": 1, "jobs": {}}


def _save_feed(feed: dict) -> None:
    jobs = list(feed.get("jobs", {}).items())
    jobs.sort(key=lambda pair: pair[1].get("captured_at", ""), reverse=True)
    feed["jobs"] = dict(jobs[:3000])
    FEED_PATH.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_record(job: dict, inventory: list[dict] | None = None) -> dict:
    link = str(job.get("link", "")).strip()
    title = str(job.get("title", "")).strip()
    page_text = title
    signal_source = "title-only"
    if link:
        try:
            fetched = _visible_page_text(link)
            if len(fetched) >= 80:
                page_text = f"{title}\n{fetched}"
                signal_source = "job-page"
        except Exception:
            pass

    skills = detect_skills(page_text, inventory=inventory)
    terms = detect_signal_terms(page_text)
    return {
        "id": job_id(link),
        "company": str(job.get("company", "")).strip(),
        "title": title,
        "location": str(job.get("location", "")).strip(),
        "apply_url": link,
        "official_url": str(job.get("official_url") or link).strip(),
        "posted": str(job.get("posted", "N/A")),
        "profile": classify_profile(title, skills),
        "detected_skills": skills,
        "signal_terms": terms,
        "signal_source": signal_source,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def prepare_portal_jobs(jobs: list[dict]) -> list[dict]:
    """Persist public job signals and return copies whose Apply URL opens portal."""
    if not jobs:
        return []
    feed = _load_feed()
    inventory = _load_inventory()
    public_jobs = []

    for job in jobs:
        link = str(job.get("link", "")).strip()
        jid = job_id(link)
        record = build_record(job, inventory=inventory)
        feed["jobs"][jid] = record

        clone = copy.deepcopy(job)
        clone["link"] = f"{PORTAL_URL}?job={quote(jid)}"
        public_jobs.append(clone)

    feed["generated_at"] = datetime.now(timezone.utc).isoformat()
    _save_feed(feed)
    return public_jobs


def install(js_module) -> None:
    """Wrap Markdown and Telegram output without changing scraper dedupe state."""
    if getattr(js_module, "_resume_portal_installed", False):
        return

    original_markdown = js_module.update_daily_markdown
    original_telegram = js_module.send_telegram

    def update_daily_markdown(jobs):
        return original_markdown(prepare_portal_jobs(jobs))

    def send_telegram(jobs, bot_token, chat_id):
        return original_telegram(prepare_portal_jobs(jobs), bot_token, chat_id)

    js_module.update_daily_markdown = update_daily_markdown
    js_module.send_telegram = send_telegram
    js_module._resume_portal_installed = True
