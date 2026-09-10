"""Backfill recent Markdown job listings into the Resume + Apply portal feed.

This is safe for the public repository: it reads only public job-list rows and
writes public job signals. It never reads the private master resume.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from resume_portal_feed import (
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


def _clean_cell(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^\*\*(.*?)\*\*$", r"\1", value)
    return value.strip()


def _direct_apply_url(url: str, feed: dict) -> str:
    if not url.startswith(PORTAL_URL):
        return url
    match = re.search(r"[?&]job=([0-9a-f]{16})", url)
    if not match:
        return url
    existing = feed.get("jobs", {}).get(match.group(1), {})
    return str(existing.get("apply_url") or url)


def _rewrite_file(path: Path, feed: dict, inventory: list[dict], portal_ready: bool) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    changed = 0
    captured = 0
    out: list[str] = []

    for line in lines:
        if "|" not in line or "[Apply](" not in line and "[Resume + Apply](" not in line:
            out.append(line)
            continue

        cells = line.strip("\r\n").split("|")
        # Expected table shape: | Company | Location | Role | Apply | ... |
        if len(cells) < 6:
            out.append(line)
            continue

        company = _clean_cell(cells[1])
        location = _clean_cell(cells[2])
        title = _clean_cell(cells[3])
        apply_cell = cells[4]
        apply_match = APPLY_RE.search(apply_cell)
        if not apply_match or not company or not title:
            out.append(line)
            continue

        shown_url = apply_match.group(1)
        direct_url = _direct_apply_url(shown_url, feed)
        if direct_url.startswith(PORTAL_URL):
            out.append(line)
            continue

        official_url = direct_url
        if len(cells) >= 7:
            official_match = LINK_RE.search(cells[5])
            if official_match:
                official_url = official_match.group(1)

        posted = _clean_cell(cells[-2]) if len(cells) >= 6 else "N/A"
        job = {
            "company": company,
            "location": location,
            "title": title,
            "link": direct_url,
            "official_url": official_url,
            "posted": posted,
        }
        jid = job_id(direct_url)
        existing = feed["jobs"].get(jid)
        if not isinstance(existing, dict) or existing.get("apply_url") != direct_url:
            feed["jobs"][jid] = build_record(job, inventory=inventory)
            captured += 1

        if portal_ready:
            portal_url = f"{PORTAL_URL}?job={quote(jid)}"
            replacement = f"[Resume + Apply]({portal_url})"
            new_apply_cell = APPLY_RE.sub(replacement, apply_cell, count=1)
            if new_apply_cell != apply_cell:
                cells[4] = new_apply_cell
                ending = "\n" if line.endswith("\n") else ""
                line = "|".join(cells) + ending
                changed += 1

        out.append(line)

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
        captured, changed = _rewrite_file(path, feed, inventory, portal_ready)
        captured_total += captured
        changed_total += changed

    feed["portal_live"] = portal_ready
    _save_feed(feed)
    print(f"Portal live: {portal_ready}")
    print(f"Captured {captured_total} existing jobs into job_signals.json")
    print(f"Rewrote {changed_total} Apply links to Resume + Apply")


if __name__ == "__main__":
    main()
