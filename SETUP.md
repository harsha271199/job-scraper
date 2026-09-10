# Setup Guide — Job Scraper

## What this scraper supports

The scraper can collect jobs from two kinds of sources:

1. **Official company career pages / APIs** — preferred when the company exposes jobs in a stable, machine-readable way.
2. **ATS backends** — Greenhouse, Lever, Ashby, and Workday when the company's public careers site uses one of them behind the scenes.

Every result may contain both:
- **Apply** — the exact job/application page.
- **Official Careers** — the employer's branded careers homepage/search page.

This means a company can still use Workday or Greenhouse internally without forcing you to browse only generic ATS URLs.

## Files

- `job_scraper.py` — scraper and filtering logic.
- `companies.csv` — large legacy ATS source list.
- `official_companies.csv` — preferred source overrides and major official career sites.
- `test_job_scraper.py` — regression tests.
- `seen_links.csv` — previously seen job URLs so Telegram alerts do not repeat jobs.

`official_companies.csv` overrides a company with the same name in `companies.csv`, so you do not need to edit the large legacy file every time a major employer changes its careers system.

## Supported platform values

### Direct official sources

- `apple` — Apple Jobs official U.S. search.
- `google` — Google Careers official search.
- `tesla` — Tesla's official careers data/search.
- `official` — generic parser for compatible server-rendered official careers pages.

### ATS sources

- `greenhouse`
- `lever`
- `ashby`
- `workday`

For an ATS row, set `official_url` to the company's branded careers page. The scraper will use the ATS for reliable collection while showing the official careers link in output.

Example:

```csv
company,platform,careers_url,official_url
SpaceX,greenhouse,https://boards.greenhouse.io/spacex,https://new.spacex.com/careers
```

## Adding or overriding a company

Add it to `official_companies.csv`:

```csv
company,platform,careers_url,official_url
Example Company,greenhouse,https://boards.greenhouse.io/example,https://example.com/careers
```

If the company already exists in `companies.csv`, the new row automatically replaces the old configuration at runtime.

For a compatible custom company careers page:

```csv
Example Company,official,https://example.com/careers/jobs,https://example.com/careers
```

## GitHub Actions

The workflow runs at the top of every hour. Before scraping it runs:

```bash
python -m unittest -v test_job_scraper.py
```

If the regression tests fail, the scrape does not run or commit bad output.

## Telegram secrets

In GitHub go to **Settings → Secrets and variables → Actions** and add:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

The hourly workflow sends new matching jobs to Telegram when both secrets exist.

## Filters

The scraper targets early/mid-career software, data, AI/ML, cloud and analytics roles and excludes senior/managerial and unrelated roles.

The U.S. location filter is intentionally conservative. A listing that says only `Remote` is not assumed to be U.S.-based; it must include a U.S. location signal. This prevents jobs such as `Remote - Canada` or `Remote, United Kingdom` from appearing as U.S. matches.
