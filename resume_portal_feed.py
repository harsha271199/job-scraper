"""One-click resume portal integration for the job scraper.

This module never reads the private master resume. It publishes only derived
job signals (title, location, detected skills, role profile, and the real apply
URL) to job_signals.json. Outward-facing Apply links are rewritten to the
browser-only resume portal only after the Pages site is actually reachable.
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
PORTAL_CHECK_TIMEOUT = 5
JD_SKILL_VERSION = 2
TOP_JD_SKILLS = 10

_SIGNAL_TERMS = (
    "data pipeline", "data pipelines", "etl", "elt", "data warehouse",
    "data lake", "distributed systems", "streaming", "kafka", "api",
    "rest api", "microservices", "cloud", "infrastructure as code", "iac",
    "ci/cd", "observability", "monitoring", "incident response",
    "root cause analysis", "data quality", "data modeling", "schema design",
    "machine learning", "deep learning", "nlp", "llm", "analytics",
    "dashboard", "business intelligence", "sql", "python",
)

# These are JD terms, not claims about the candidate. They let the public feed
# recognize requirements that are not yet present in the private resume master.
_JD_EXTRA_SKILLS: dict[str, tuple[str, ...]] = {
    "Data Warehousing": ("data warehouse", "data warehousing"),
    "Data Lakes": ("data lake", "data lakes"),
    "Distributed Systems": ("distributed systems", "distributed system"),
    "Streaming Systems": ("streaming systems", "real-time streaming", "stream processing"),
    "Microservices": ("microservices", "microservice architecture"),
    "Cloud Computing": ("cloud computing", "cloud platforms"),
    "Observability": ("observability",),
    "Monitoring": ("monitoring",),
    "Deep Learning": ("deep learning",),
    "NLP": ("natural language processing", "NLP"),
    "Large Language Models": ("large language models", "large language model", "LLMs", "LLM"),
    "Generative AI": ("generative AI", "genAI", "gen AI"),
    "Retrieval-Augmented Generation": ("retrieval-augmented generation", "retrieval augmented generation", "RAG"),
    "Computer Vision": ("computer vision",),
    "scikit-learn": ("scikit-learn", "sklearn"),
    "TensorFlow": ("TensorFlow",),
    "Keras": ("Keras",),
    "MLOps": ("MLOps", "ML Ops"),
    "Model Deployment": ("model deployment", "deploy models", "productionize models"),
    "Feature Engineering": ("feature engineering",),
    "Statistics": ("statistics", "statistical analysis", "statistical modeling"),
    "Experimentation": ("experimentation", "experiments"),
    "A/B Testing": ("A/B testing", "A/B tests", "AB testing"),
    "MLflow": ("MLflow",),
    "Vector Databases": ("vector database", "vector databases", "vector store", "vector stores"),
    "Hadoop": ("Hadoop",),
    "Hive": ("Apache Hive", "Hive"),
    "Trino": ("Trino", "Presto"),
    "Apache Flink": ("Apache Flink", "Flink"),
    "NoSQL": ("NoSQL", "non-relational database", "non relational database"),
    "MongoDB": ("MongoDB",),
    "Redis": ("Redis",),
    "MySQL": ("MySQL",),
    "Oracle": ("Oracle Database", "Oracle SQL", "Oracle"),
    "Data Governance": ("data governance",),
    "Data Architecture": ("data architecture",),
    "Data Visualization": ("data visualization", "visualization", "visualisations", "visualizations"),
    "Business Intelligence": ("business intelligence", "BI reporting"),
    "Dashboarding": ("dashboarding", "dashboards", "dashboard development"),
    "Power BI": ("Power BI",),
    "Looker": ("Looker",),
    "Linux": ("Linux",),
    "Jenkins": ("Jenkins",),
    "Ansible": ("Ansible",),
    "Prometheus": ("Prometheus",),
    "Grafana": ("Grafana",),
    "Networking": ("networking", "computer networks", "network infrastructure"),
    "System Design": ("system design", "systems design"),
    "Testing": ("unit testing", "integration testing", "automated testing", "test automation"),
    "Node.js": ("Node.js", "NodeJS", "Node JS"),
    "Spring Boot": ("Spring Boot",),
    ".NET": (".NET", "dotnet"),
    "C#": ("C#",),
    "GitLab": ("GitLab",),
    "Argo CD": ("Argo CD", "ArgoCD"),
    "CloudFormation": ("CloudFormation", "AWS CloudFormation"),
    "Serverless": ("serverless", "serverless architecture"),
    "AWS Lambda": ("AWS Lambda", "Lambda functions"),
    "Agile": ("Agile", "Agile development"),
    "Scrum": ("Scrum",),
    "Stakeholder Management": ("stakeholder management", "stakeholder communication", "stakeholders"),
    "Communication": ("communication skills", "written and verbal communication", "written communication", "verbal communication"),
    "Problem Solving": ("problem solving", "problem-solving"),
    "Collaboration": ("cross-functional collaboration", "collaboration", "collaborative"),
}

_SOFT_JD_SKILLS = {
    "Agile", "Scrum", "Stakeholder Management", "Communication",
    "Problem Solving", "Collaboration",
}

_REQUIREMENT_MARKERS = (
    "required", "requirements", "qualification", "qualifications", "preferred",
    "must have", "nice to have", "experience with", "experience in",
    "proficiency", "proficient", "knowledge of", "familiarity with",
    "skills", "you have", "we are looking for",
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_portal_live_cache: bool | None = None


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def job_id(link: str) -> str:
    return hashlib.sha256(str(link).encode("utf-8")).hexdigest()[:16]


def portal_is_live(*, force: bool = False) -> bool:
    """Return True only when the deployed Pages portal is reachable."""
    global _portal_live_cache
    if _portal_live_cache is not None and not force:
        return _portal_live_cache
    try:
        response = requests.get(
            PORTAL_URL,
            headers=_HEADERS,
            timeout=PORTAL_CHECK_TIMEOUT,
            allow_redirects=True,
        )
        body = response.text.casefold() if response.ok else ""
        _portal_live_cache = bool(
            response.ok
            and "resume + apply" in body
            and "private master resume" in body
        )
    except Exception:
        _portal_live_cache = False
    return _portal_live_cache


def classify_profile(title: str, skills: list[str] | None = None) -> str:
    """Classify from the title first; use detected skills only as fallback."""
    title_text = str(title or "").casefold()
    checks = (
        ("machine-learning", ("data scientist", "machine learning", "ml engineer", "ai engineer", "applied scientist", "nlp engineer", "llm engineer")),
        ("data-engineering", ("data engineer", "analytics engineer", "etl engineer", "pipeline engineer", "big data engineer")),
        ("data-analytics", ("data analyst", "business analyst", "business intelligence", "bi analyst", "product analyst", "growth analyst", "reporting analyst")),
        ("cloud-devops", ("cloud engineer", "devops", "site reliability", "sre", "platform engineer")),
        ("software-engineering", ("software engineer", "software developer", "backend engineer", "swe", "sde")),
    )
    for profile, terms in checks:
        if any(term in title_text for term in terms):
            return profile

    skill_text = " ".join(skills or []).casefold()
    if any(x in skill_text for x in ("machine learning", "pytorch", "hugging face", "tensorflow")):
        return "machine-learning"
    if any(x in skill_text for x in ("apache airflow", "dbt", "kafka", "etl/elt", "data warehousing")):
        return "data-engineering"
    if any(x in skill_text for x in ("terraform", "kubernetes", "docker", "microsoft azure", "jenkins", "ansible")):
        return "cloud-devops"
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


def _safe_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", re.I)


def detect_skills(text: str, inventory: list[dict] | None = None, limit: int = 24) -> list[str]:
    """Detect skills known to the resume inventory."""
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
            count += len(_safe_pattern(alias).findall(haystack))
        if count:
            ranked.append((count, str(item["name"])))
    ranked.sort(key=lambda x: (-x[0], x[1].casefold()))
    return [name for _, name in ranked[:limit]]


def _jd_catalog(inventory: list[dict]) -> dict[str, list[str]]:
    catalog: dict[str, list[str]] = {}
    for item in inventory:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        catalog[name] = _unique([name, *[str(a) for a in item.get("aliases", [])]])
    for name, aliases in _JD_EXTRA_SKILLS.items():
        catalog[name] = _unique([*(catalog.get(name) or []), name, *aliases])
    return catalog


def detect_jd_skills(
    text: str,
    inventory: list[dict] | None = None,
    limit: int = TOP_JD_SKILLS,
) -> list[str]:
    """Rank skills that are actually written in the job description.

    The catalog is intentionally broader than the resume inventory so a JD skill
    can still be shown for user confirmation even when it is absent from the
    private master resume.
    """
    inventory = inventory if inventory is not None else _load_inventory()
    haystack = str(text or "")
    low = haystack.casefold()
    ranked: list[tuple[int, int, str]] = []

    for name, aliases in _jd_catalog(inventory).items():
        score = 0
        first_pos = len(haystack) + 1
        matched = False
        for alias in aliases:
            alias = alias.strip()
            if not alias or (len(alias) == 1 and alias.isalpha()):
                continue
            for match in _safe_pattern(alias).finditer(haystack):
                matched = True
                first_pos = min(first_pos, match.start())
                score += 10
                window = low[max(0, match.start() - 220): min(len(low), match.end() + 220)]
                if any(marker in window for marker in _REQUIREMENT_MARKERS):
                    score += 7
        if not matched:
            continue
        if name in _SOFT_JD_SKILLS:
            score -= 6
        ranked.append((score, first_pos, name))

    ranked.sort(key=lambda x: (-x[0], x[1], x[2].casefold()))
    return [name for _, _, name in ranked[:limit]]


def _verification_split(skills: list[str], inventory: list[dict]) -> tuple[list[str], list[str]]:
    status = {str(item.get("name", "")).casefold(): bool(item.get("verified", False)) for item in inventory}
    verified, gaps = [], []
    for skill in skills:
        (verified if status.get(skill.casefold(), False) else gaps).append(skill)
    return verified, gaps


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
    inventory = inventory if inventory is not None else _load_inventory()
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

    inventory_skills = detect_skills(page_text, inventory=inventory)
    top_jd_skills = detect_jd_skills(page_text, inventory=inventory)
    skills = _unique([*top_jd_skills, *inventory_skills])[:24]
    verified_skills, unverified_skills = _verification_split(skills, inventory)
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
        "top_jd_skills": top_jd_skills,
        "verified_skills": verified_skills,
        "unverified_skills": unverified_skills,
        "signal_terms": terms,
        "signal_source": signal_source,
        "jd_skill_version": JD_SKILL_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def prepare_portal_jobs(jobs: list[dict]) -> list[dict]:
    """Persist public job signals and route outward links when portal is live."""
    if not jobs:
        return []
    feed = _load_feed()
    inventory = _load_inventory()
    public_jobs = []
    portal_ready = portal_is_live()

    for job in jobs:
        link = str(job.get("link", "")).strip()
        jid = job_id(link)
        existing = feed["jobs"].get(jid)
        current = (
            isinstance(existing, dict)
            and existing.get("apply_url") == link
            and existing.get("jd_skill_version") == JD_SKILL_VERSION
        )
        if current:
            record = existing
        else:
            record = build_record(job, inventory=inventory)
            feed["jobs"][jid] = record

        clone = copy.deepcopy(job)
        if portal_ready:
            clone["link"] = f"{PORTAL_URL}?job={quote(jid)}"
        public_jobs.append(clone)

    feed["generated_at"] = datetime.now(timezone.utc).isoformat()
    feed["portal_live"] = portal_ready
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
