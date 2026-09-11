"""Backfill recent Markdown job listings into the Resume + Apply portal feed.

This is safe for the public repository: it reads only public job-list rows and
writes public job signals. It never reads the private master resume.

The Markdown output intentionally keeps BOTH actions:
- Apply: opens the original job posting so the full JD can be reviewed.
- Resume + Apply: opens the browser-only tailoring portal for that exact job.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from resume_portal_feed import (
    JD_SKILL_VERSION,
    PORTAL_URL,
    _load_feed,
    _load_inventory,
    _save_feed,
    build_record,
    job_id,
    portal_is_live,
)

APPLY_RE = re.compile(r"\[(?:Apply|Resume \+ Apply)\]\((https?://[^)]+)\)", re.I)
LINK_RE = re.compile(r"\[[^]]+\]\((https?://[^)]+)\)")
HEADER = "| 🏢 Company | 📍 Location | 💼 Role | 🔗 Apply | 📄 Resume + Apply | 🏠 Official Careers | 📅 Posted |\n"
SEPARATOR = "|---|---|---|---|---|---|---|\n"


def _clean_cell(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^\*\*(.*?)\*\*$", r"\1", value)
    return value.strip()


def _direct_apply_url(url: str, feed: dict) -> str:
    """Recover the original job URL when a legacy row points to the portal."""
    if not url.startswith(PORTAL_URL):
        return url
    match = re.search(r"[?&]job=([0-9a-f]{16})", url)
    if not match:
        return url
    existing = feed.get("jobs", {}).get(match.group(1), {})
    return str(existing.get("apply_url") or url)


def _link_from_cell(value: str) -> str:
    match = LINK_RE.search(value or "")
    return match.group(1) if match else ""


def _rewrite_file(
    path: Path,
    feed: dict,
    inventory: list[dict],
    portal_ready: bool,
    refresh_stale: bool = False,
) -> tuple[int, int]:
    """Normalize job tables and optionally refresh stale JD-skill records."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    changed = 0
    captured = 0
    out: list[str] = []
    expect_separator = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("| 🏢 Company |") and ("🔗 Apply" in stripped or "🔗 Link" in stripped):
            if line != HEADER:
                changed += 1
            out.append(HEADER)
            expect_separator = True
            continue

        if expect_separator and re.fullmatch(r"\|(?:\s*:?-+:?\s*\|){5,8}", stripped):
            if line != SEPARATOR:
                changed += 1
            out.append(SEPARATOR)
            expect_separator = False
            continue
        expect_separator = False

        if "|" not in line or ("[Apply](" not in line and "[Resume + Apply](" not in line):
            out.append(line)
            continue

        raw_cells = line.strip("\r\n").split("|")
        if len(raw_cells) < 7:
            out.append(line)
            continue

        logical = raw_cells[1:-1]
        if len(logical) < 5:
            out.append(line)
            continue

        company_display = logical[0].strip()
        location_display = logical[1].strip()
        title_display = logical[2].strip()
        company = _clean_cell(company_display)
        location = _clean_cell(location_display)
        title = _clean_cell(title_display)

        apply_cell = logical[3]
        if len(logical) >= 7:
            official_cell = logical[5]
            posted_display = logical[6].strip()
        elif len(logical) == 6:
            official_cell = logical[4]
            posted_display = logical[5].strip()
        else:
            official_cell = ""
            posted_display = logical[4].strip()

        apply_match = APPLY_RE.search(apply_cell)
        if not apply_match or not company or not title:
            out.append(line)
            continue

        shown_url = apply_match.group(1)
        direct_url = _direct_apply_url(shown_url, feed)
        if direct_url.startswith(PORTAL_URL):
            out.append(line)
            continue

        jid = job_id(direct_url)
        existing = feed.get("jobs", {}).get(jid)
        official_url = _link_from_cell(official_cell)
        stale = (
            not isinstance(existing, dict)
            or (refresh_stale and existing.get("jd_skill_version") != JD_SKILL_VERSION)
        )

        if stale:
            job = {
                "company": company,
                "location": location,
                "title": title,
                "link": direct_url,
                "official_url": (
                    str(existing.get("official_url"))
                    if isinstance(existing, dict) and existing.get("official_url")
                    else (official_url or direct_url)
                ),
                "posted": _clean_cell(posted_display) or "N/A",
            }
            feed["jobs"][jid] = build_record(job, inventory=inventory)
            existing = feed["jobs"][jid]
            captured += 1

        official_url = str(existing.get("official_url") or official_url or direct_url)

        direct_cell = f"[Apply]({direct_url})"
        if portal_ready:
            resume_url = f"{PORTAL_URL}?job={quote(jid)}"
            resume_cell = f"[Resume + Apply]({resume_url})"
        else:
            resume_cell = "Portal unavailable"
        careers_cell = f"[Careers]({official_url})" if official_url else "N/A"

        new_line = (
            f"| {company_display} | {location_display} | {title_display} | "
            f"{direct_cell} | {resume_cell} | {careers_cell} | {posted_display} |\n"
        )
        if new_line != line:
            changed += 1
        out.append(new_line)

    new_text = "".join(out)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return captured, changed


def main() -> None:
    feed = _load_feed()
    inventory = _load_inventory()
    portal_ready = portal_is_live(force=True)

    files = [Path("README.md"), *sorted(Path(".").glob("*-Jobs-List.md"))]
    captured_total = 0
    changed_total = 0
    seen_paths: set[Path] = set()
    for path in files:
        if path in seen_paths or not path.exists():
            continue
        seen_paths.add(path)
        captured, changed = _rewrite_file(
            path,
            feed,
            inventory,
            portal_ready,
            refresh_stale=True,
        )
        captured_total += captured
        changed_total += changed

    feed["portal_live"] = portal_ready
    _save_feed(feed)
    print(f"Portal live: {portal_ready}")
    print(f"Captured/refreshed {captured_total} jobs into job_signals.json")
    print(f"Rewrote {changed_total} table rows/headers with separate Apply and Resume + Apply links")


if __name__ == "__main__":
    main()
