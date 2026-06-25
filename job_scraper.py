"""
Job Scraper for Harshavardhan Kagithoju
Hits ATS APIs directly — Greenhouse, Lever, Workday, Ashby
Runs every hour via GitHub Actions → sends Telegram alert
"""

import time
import random
import csv
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── KEYWORDS TO MATCH (job titles you want) ─────────────────────────────────
KEYWORDS = [
    'data engineer', 'data engineering',
    'data scientist', 'data science',
    'machine learning', 'ml engineer',
    'ai engineer', 'artificial intelligence',
    'software engineer', 'software developer', 'sde', 'swe',
    'platform engineer', 'cloud engineer',
    'backend engineer', 'backend developer',
    'data analyst', 'analytics engineer',
    'mlops', 'llm', 'generative ai', 'genai',
    'nlp engineer', 'applied scientist',
    'data infrastructure', 'big data',
    'python developer', 'python engineer',
    'intern', 'internship', 'new grad', 'entry level',
    'associate engineer', 'junior engineer',
]

# ─── KEYWORDS TO EXCLUDE (roles you don't want) ───────────────────────────────
NO_KEYWORDS = [
    'senior', 'sr.', ' sr ', 'staff', 'principal', 'director',
    'manager', 'lead', 'vp', 'vice president', 'head of',
    'c++', 'embedded', 'firmware', 'hardware',
    'sales', 'marketing', 'recruiter', 'finance',
    'security engineer', 'network engineer',
    'mechanical', 'civil', 'electrical',
    'nurse', 'legal', 'accounting',
    'ui/ux', 'ux designer', 'graphic',
]

# ─── ERROR LOGGING ────────────────────────────────────────────────────────────
error_messages = []

def log_error(company, message):
    if len(message) > 300:
        message = message[:300] + '...'
    error_messages.append(f"[ERROR] {company}: {message}")

# ─── KEYWORD MATCHING ─────────────────────────────────────────────────────────
def keyword_match(title):
    title_lower = title.lower()
    has_positive = any(k in title_lower for k in KEYWORDS)
    has_negative = any(nk in title_lower for nk in NO_KEYWORDS)
    return has_positive and not has_negative

# ─── US LOCATION FILTER ───────────────────────────────────────────────────────
def is_us_location(location):
    if not location:
        return True
    loc = location.lower()
    us_keywords = ['united states', 'usa', ' us ', 'remote', 'us-', '- us']
    us_states = [
        'alabama','alaska','arizona','arkansas','california','colorado',
        'connecticut','delaware','florida','georgia','hawaii','idaho',
        'illinois','indiana','iowa','kansas','kentucky','louisiana','maine',
        'maryland','massachusetts','michigan','minnesota','mississippi',
        'missouri','montana','nebraska','nevada','new hampshire','new jersey',
        'new mexico','new york','north carolina','north dakota','ohio',
        'oklahoma','oregon','pennsylvania','rhode island','south carolina',
        'south dakota','tennessee','texas','utah','vermont','virginia',
        'washington','west virginia','wisconsin','wyoming','tempe','phoenix',
        'seattle','san francisco','new york city','austin','chicago',
        'boston','los angeles','denver','atlanta','dallas','houston',
    ]
    abbrs = ['al','ak','az','ar','ca','co','ct','de','fl','ga','hi','id',
             'il','in','ia','ks','ky','la','me','md','ma','mi','mn','ms',
             'mo','mt','ne','nv','nh','nj','nm','ny','nc','nd','oh','ok',
             'or','pa','ri','sc','sd','tn','tx','ut','vt','va','wa','wv','wi','wy']
    return (
        any(k in loc for k in us_keywords)
        or any(s in loc for s in us_states)
        or any(re.search(r'\b' + a + r'\b', loc) for a in abbrs)
        or re.search(r',\s*us$', loc)
    )

# ─── SCRAPERS ─────────────────────────────────────────────────────────────────
results = []
old_links = set()

def scrape_greenhouse(url, company):
    try:
        match = re.search(r'greenhouse.io/([^/?\s]+)', url)
        if not match:
            log_error(company, "Bad Greenhouse URL")
            return
        org = match.group(1)
        r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{org}/jobs", timeout=10)
        if r.status_code != 200:
            log_error(company, f"Greenhouse {r.status_code}")
            return
        for job in r.json().get('jobs', []):
            title = job.get('title', '')
            location = job.get('location', {}).get('name', 'N/A')
            link = job.get('absolute_url', '')
            posted = job.get('first_published', 'N/A')
            if keyword_match(title) and link not in old_links and is_us_location(location):
                results.append({'company': company, 'title': title,
                                'location': location, 'link': link, 'posted': posted})
                old_links.add(link)
    except Exception as e:
        log_error(company, str(e))

def scrape_lever(url, company):
    try:
        match = re.search(r'lever.co/([^/?\s]+)', url)
        if not match:
            log_error(company, "Bad Lever URL")
            return
        org = match.group(1)
        r = requests.get(f"https://api.lever.co/v0/postings/{org}?mode=json", timeout=10)
        if r.status_code != 200:
            log_error(company, f"Lever {r.status_code}")
            return
        for job in r.json():
            title = job.get('text', '')
            location = job.get('categories', {}).get('location', 'N/A')
            link = job.get('hostedUrl', '')
            created = job.get('createdAt')
            posted = datetime.utcfromtimestamp(created/1000).strftime('%Y-%m-%d %H:%M') if created else 'N/A'
            if keyword_match(title) and link not in old_links and is_us_location(location):
                results.append({'company': company, 'title': title,
                                'location': location, 'link': link, 'posted': posted})
                old_links.add(link)
    except Exception as e:
        log_error(company, str(e))

def scrape_ashby(url, company):
    try:
        match = re.search(r'ashbyhq\.com/([\w\-]+)', url)
        if not match:
            log_error(company, "Bad Ashby URL")
            return
        org = match.group(1)
        r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{org}", timeout=10)
        if r.status_code != 200:
            log_error(company, f"Ashby {r.status_code}")
            return
        for job in r.json().get('jobs', []):
            title = job.get('title', '')
            location = job.get('location', 'N/A')
            link = job.get('jobUrl', '')
            posted = job.get('publishedAt', 'N/A')
            if keyword_match(title) and link not in old_links and is_us_location(location):
                results.append({'company': company, 'title': title,
                                'location': location, 'link': link, 'posted': posted})
                old_links.add(link)
    except Exception as e:
        log_error(company, str(e))

def scrape_workday(url, company):
    try:
        match = re.search(r'https://([\w\-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[\w\-]+/)?([\w\-]+)', url)
        if not match:
            log_error(company, "Bad Workday URL")
            return
        sub, wd, site = match.group(1), match.group(2), match.group(3)
        api = f"https://{sub}.{wd}.myworkdayjobs.com/wday/cxs/{sub}/{site}/jobs"
        offset, page = 0, 20
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        while True:
            time.sleep(random.uniform(1.5, 3.0))
            r = requests.post(api, json={"appliedFacets": {}, "limit": page,
                              "offset": offset, "searchText": ""}, headers=headers, timeout=15)
            if r.status_code != 200:
                log_error(company, f"Workday {r.status_code}")
                break
            data = r.json()
            postings = data.get('jobPostings', [])
            if not postings:
                break
            for job in postings:
                title = job.get('title', '')
                location = job.get('locationsText', 'N/A')
                path = job.get('externalPath', '')
                posted = job.get('postedOn', 'N/A')
                link = f"https://{sub}.{wd}.myworkdayjobs.com/en-US/{site}{path}"
                if keyword_match(title) and link not in old_links and is_us_location(location):
                    results.append({'company': company, 'title': title,
                                    'location': location, 'link': link, 'posted': posted})
                    old_links.add(link)
            offset += page
            if offset >= data.get('total', 0):
                break
    except Exception as e:
        log_error(company, str(e))

def scrape_company(row):
    platform = str(row.get('platform', '')).lower().strip()
    url = str(row.get('careers_url', '')).strip()
    company = str(row.get('company', '')).strip()
    dispatch = {
        'greenhouse': scrape_greenhouse,
        'lever': scrape_lever,
        'ashby': scrape_ashby,
        'workday': scrape_workday,
    }
    fn = dispatch.get(platform)
    if fn:
        fn(url, company)
    else:
        log_error(company, f"Unsupported platform: {platform}")

# ─── MARKDOWN OUTPUT ──────────────────────────────────────────────────────────
def get_daily_filename():
    now = datetime.now()
    return f"{now.day}-{now.strftime('%B')}-Jobs-List.md"

def update_daily_markdown(new_jobs):
    if not new_jobs:
        print("No new jobs found this batch.")
        return
    daily_file = get_daily_filename()
    batch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    anchor = f"batch-{batch_time.replace(' ', '-').replace(':', '-')}"

    # Count per company
    company_counts = {}
    for j in new_jobs:
        company_counts[j['company']] = company_counts.get(j['company'], 0) + 1

    summary = f"\n📊 **{len(new_jobs)} new jobs this batch:**\n"
    for c, n in sorted(company_counts.items()):
        summary += f"- {c}: {n} job{'s' if n > 1 else ''}\n"

    table = "| 🏢 Company | 📍 Location | 💼 Role | 🔗 Link | 📅 Posted |\n"
    table += "|---|---|---|---|---|\n"
    for j in new_jobs:
        table += f"| **{j['company']}** | {j['location']} | {j['title']} | [Apply]({j['link']}) | {j['posted']} |\n"

    batch_block = f"\n### 🕐 Batch at {batch_time}\n{summary}\n{table}\n---\n"

    # Prepend to file
    existing = ""
    if Path(daily_file).exists():
        with open(daily_file, 'r') as f:
            content = f.read()
            # Strip header lines to re-add fresh
            lines = content.split('\n')
            existing = '\n'.join(lines)

    today_str = datetime.now().strftime('%B %d, %Y')
    header = f"# 📢 Job Listings for Harsha — {today_str}\n> Updated every hour. Newest batch first.\n"

    with open(daily_file, 'w') as f:
        f.write(header + batch_block + existing)

    # Mirror to README
    with open(daily_file, 'r') as src, open('README.md', 'w') as dst:
        dst.write(src.read())

    print(f"✅ {len(new_jobs)} new jobs written to {daily_file} and README.md")

# ─── TELEGRAM NOTIFICATION ────────────────────────────────────────────────────
def send_telegram(new_jobs, bot_token, chat_id):
    if not new_jobs:
        return
    msg = f"🚀 *{len(new_jobs)} NEW JOBS — {datetime.now().strftime('%b %d %H:%M')}*\n\n"
    for j in new_jobs[:15]:  # Telegram has message length limits
        msg += f"🏢 *{j['company']}*\n"
        msg += f"💼 {j['title']}\n"
        msg += f"📍 {j['location']}\n"
        msg += f"🔗 [Apply]({j['link']})\n\n"
    if len(new_jobs) > 15:
        msg += f"_...and {len(new_jobs) - 15} more. Check README._"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os

    # Load seen links
    old_path = Path('seen_links.csv')
    if old_path.exists():
        try:
            old_df = pd.read_csv(old_path)
            old_links = set(old_df['link'].dropna().unique())
        except:
            old_links = set()

    # Load companies
    companies_df = pd.read_csv('companies.csv')
    print(f"Scraping {len(companies_df)} companies...")

    # Scrape in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(scrape_company, row) for _, row in companies_df.iterrows()]
        for f in as_completed(futures):
            pass

    print(f"Found {len(results)} new jobs")

    # Update markdown
    update_daily_markdown(results)

    # Save new seen links
    if results:
        new_df = pd.DataFrame(results)
        new_df[['link']].to_csv(old_path, mode='a', index=False,
                                 header=not old_path.exists())

    # Send Telegram
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if bot_token and chat_id:
        send_telegram(results, bot_token, chat_id)
    else:
        print("No Telegram credentials — skipping notification")

    # Print errors
    if error_messages:
        print("\n--- ERRORS ---")
        for e in error_messages[:10]:
            print(e)
