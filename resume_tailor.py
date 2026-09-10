#!/usr/bin/env python3
"""Deterministically tailor a resume Skills section to a job description.

This module intentionally does not call any generative-AI service. It ranks
skills from a maintained inventory, inserts only skills marked verified=True,
and reports requested-but-unverified skills separately so the resume never
claims experience the candidate does not have.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable


DEFAULT_INVENTORY = Path(__file__).with_name("resume_skill_inventory.json")


def _alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias.strip())
    # Use alphanumeric lookarounds instead of \b so aliases such as C++,
    # CI/CD, and scikit-learn still match correctly.
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.I)


def _count_alias(text: str, alias: str) -> int:
    return len(_alias_pattern(alias).findall(text))


def load_inventory(path: str | Path = DEFAULT_INVENTORY) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    skills = data.get("skills", [])
    if not isinstance(skills, list):
        raise ValueError("inventory must contain a 'skills' list")

    normalized = []
    seen = set()
    for item in skills:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        name = str(item["name"]).strip()
        key = name.casefold()
        if key in seen:
            raise ValueError(f"duplicate skill in inventory: {name}")
        seen.add(key)
        aliases = [name]
        aliases.extend(str(a).strip() for a in item.get("aliases", []) if str(a).strip())
        normalized.append(
            {
                "name": name,
                "aliases": list(dict.fromkeys(aliases)),
                "verified": bool(item.get("verified", False)),
            }
        )
    return normalized


def rank_jd_skills(jd_text: str, inventory: Iterable[dict]) -> list[dict]:
    """Rank inventory skills by deterministic evidence in the JD.

    Frequency is the base score. Mentions on qualification/requirement lines get
    a small boost because those tend to influence ATS qualification matching.
    """
    lines = [line.strip() for line in jd_text.splitlines() if line.strip()]
    priority_markers = (
        "required",
        "requirement",
        "qualification",
        "minimum",
        "preferred",
        "experience with",
        "proficient",
        "proficiency",
        "must have",
    )

    ranked = []
    for skill in inventory:
        aliases = skill["aliases"]
        count = sum(_count_alias(jd_text, alias) for alias in aliases)
        if count <= 0:
            continue

        priority_hits = 0
        matched_aliases = []
        for alias in aliases:
            alias_count = _count_alias(jd_text, alias)
            if alias_count:
                matched_aliases.append(alias)
            for line in lines:
                if _count_alias(line, alias) and any(marker in line.casefold() for marker in priority_markers):
                    priority_hits += 1

        ranked.append(
            {
                "name": skill["name"],
                "verified": skill["verified"],
                "count": count,
                "priority_hits": priority_hits,
                "score": count + (priority_hits * 3),
                "matched_aliases": matched_aliases,
            }
        )

    ranked.sort(key=lambda item: (-item["score"], -item["count"], item["name"].casefold()))
    return ranked


def select_verified_skills(ranked: list[dict], max_skills: int = 15) -> list[str]:
    return [item["name"] for item in ranked if item["verified"]][:max_skills]


def select_unverified_gaps(ranked: list[dict], max_items: int = 15) -> list[str]:
    return [item["name"] for item in ranked if not item["verified"]][:max_items]


def _skills_heading(line: str) -> bool:
    stripped = line.strip()
    return bool(
        re.fullmatch(r"#{1,6}\s*skills\s*", stripped, flags=re.I)
        or re.fullmatch(r"\*\*skills\*\*\s*", stripped, flags=re.I)
        or re.fullmatch(r"skills\s*", stripped, flags=re.I)
    )


def _looks_like_next_section(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r"^#{1,6}\s+\S", stripped):
        return True
    # Plain-text resumes often use ALL-CAPS section headings.
    if len(stripped) <= 60 and stripped.upper() == stripped and re.search(r"[A-Z]", stripped):
        return True
    return False


def replace_skills_section(resume_text: str, skills: list[str]) -> str:
    """Replace the resume Skills section while preserving the rest verbatim."""
    lines = resume_text.splitlines()
    skill_line = ", ".join(skills)

    for i, line in enumerate(lines):
        if not _skills_heading(line):
            continue

        end = i + 1
        while end < len(lines) and not _looks_like_next_section(lines[end]):
            end += 1

        replacement = [line, skill_line]
        return "\n".join(lines[:i] + replacement + lines[end:]).rstrip() + "\n"

    # If a resume has no skills section, append one instead of altering other
    # content or guessing where it belongs.
    heading = "## Skills" if any(line.lstrip().startswith("#") for line in lines) else "SKILLS"
    base = resume_text.rstrip()
    return f"{base}\n\n{heading}\n{skill_line}\n"


def build_report(jd_text: str, inventory: list[dict], max_skills: int = 15) -> dict:
    ranked = rank_jd_skills(jd_text, inventory)
    selected = select_verified_skills(ranked, max_skills=max_skills)
    gaps = select_unverified_gaps(ranked, max_items=max_skills)
    return {
        "selected_verified_skills": selected,
        "requested_but_unverified": gaps,
        "ranked_jd_skills": ranked,
        "selected_count": len(selected),
        "max_skills": max_skills,
        "notes": [
            "Only skills marked verified=true are inserted into the resume.",
            "No generative AI or hidden keyword stuffing is used by this tool.",
        ],
    }


def tailor_resume(
    resume_text: str,
    jd_text: str,
    inventory: list[dict],
    max_skills: int = 15,
) -> tuple[str, dict]:
    report = build_report(jd_text, inventory, max_skills=max_skills)
    tailored = replace_skills_section(resume_text, report["selected_verified_skills"])
    return tailored, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Tailor an ATS-safe Skills section to a JD")
    parser.add_argument("--resume", required=True, help="Base resume in plain text or Markdown")
    parser.add_argument("--jd", required=True, help="Job description text file")
    parser.add_argument("--out", required=True, help="Tailored resume output path")
    parser.add_argument("--report", help="Optional JSON match/gap report path")
    parser.add_argument("--inventory", default=str(DEFAULT_INVENTORY), help="Skill inventory JSON")
    parser.add_argument("--max-skills", type=int, default=15)
    args = parser.parse_args()

    resume_text = Path(args.resume).read_text(encoding="utf-8")
    jd_text = Path(args.jd).read_text(encoding="utf-8")
    inventory = load_inventory(args.inventory)
    tailored, report = tailor_resume(resume_text, jd_text, inventory, max_skills=args.max_skills)

    Path(args.out).write_text(tailored, encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Selected {report['selected_count']} verified JD skills")
    if report["selected_verified_skills"]:
        print("Resume skills:", ", ".join(report["selected_verified_skills"]))
    if report["requested_but_unverified"]:
        print("JD gaps (not inserted):", ", ".join(report["requested_but_unverified"]))


if __name__ == "__main__":
    main()
