"""One-time cleanup for the malformed Opendoor batch produced on 2026-09-09.

The cleanup only runs when the exact bad-batch marker is present, so after the
repository is repaired subsequent scraper runs are no-ops.
"""

from __future__ import annotations

from pathlib import Path

BAD_MARKER = "- Opendoor: 54 jobs"
BATCH_HEADER = "### 🕐 Batch at 2026-09-09 18:25:52 MST"
OPENDOOR_PREFIX = "https://www.opendoor.com/careers/open-positions/jobs/"


def _clean_batch_text(text: str) -> tuple[str, bool]:
    if BAD_MARKER not in text or BATCH_HEADER not in text:
        return text, False

    start = text.find(BATCH_HEADER)
    end = text.find("\n---\n", start)
    if start < 0 or end < 0:
        return text, False

    batch = text[start:end]
    cleaned_lines = []
    for line in batch.splitlines():
        if line == BAD_MARKER:
            continue
        if line.startswith("| **Opendoor** |"):
            continue
        if line == "📊 **56 new jobs this batch:**":
            line = "📊 **2 new jobs this batch:**"
        cleaned_lines.append(line)

    cleaned_batch = "\n".join(cleaned_lines)
    return text[:start] + cleaned_batch + text[end:], True


def _clean_markdown(path: Path) -> bool:
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8")
    cleaned, changed = _clean_batch_text(original)
    if changed:
        path.write_text(cleaned, encoding="utf-8")
    return changed


def _clean_seen_links(path: Path) -> bool:
    if not path.exists():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if OPENDOOR_PREFIX not in line]
    if kept == lines:
        return False
    suffix = "\n" if kept else ""
    path.write_text("\n".join(kept) + suffix, encoding="utf-8")
    return True


def cleanup() -> bool:
    readme = Path("README.md")
    if not readme.exists() or BAD_MARKER not in readme.read_text(encoding="utf-8"):
        return False

    changed = _clean_markdown(readme)
    for path in Path(".").glob("*-Jobs-List.md"):
        changed = _clean_markdown(path) or changed
    changed = _clean_seen_links(Path("seen_links.csv")) or changed
    return changed


if __name__ == "__main__":
    if cleanup():
        print("Cleaned malformed Opendoor batch and reset its seen links")
    else:
        print("No Opendoor cleanup needed")
