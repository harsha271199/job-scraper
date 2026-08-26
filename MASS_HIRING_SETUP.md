# Hourly Mass-Hiring / Early-Career Watch

This build preserves the original hourly scraper and `seen_links.csv` behavior.

## Added behavior
- Runs every hour as before.
- Watches the full existing company list plus additional curated employers.
- Expanded Data Engineering, Cloud/Platform/DevOps/SRE, Analytics/BI, Data Science/AI, and SWE title coverage.
- Detects cohort keywords such as New Grad, University Graduate, Early Career, Development Program, Rotational Program, Campus Hire, and 2027 Graduate.
- Detects a hiring burst when one employer produces 5+ matching unseen roles in one hourly run.
- Writes `mass_hiring_signals.csv` and `MASS-HIRING-WATCH.md`.
- Telegram messages show mass/cohort signals before individual jobs.

## Important
A hiring-burst signal is an automated lead, not proof that a company is conducting a formal mass-hiring event. Apply links remain the ATS/company links already used by the scraper.

Keep your existing `seen_links.csv` when upgrading. Do not reset it unless you intentionally want all current jobs to be treated as unseen.
