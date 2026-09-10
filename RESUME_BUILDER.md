# Full ATS Resume Builder

This extends `resume_tailor.py` from skill-only matching into a complete, deterministic resume-selection workflow.

## What it does

Given one job description and a private master resume fact bank, `resume_builder.py`:

1. ranks JD skills and qualification lines;
2. selects up to 15 verified JD-matching skills;
3. scores your existing verified experience bullets against the JD;
4. selects the strongest existing bullets for each job;
5. selects the most relevant existing projects;
6. preserves employer names, job titles, dates, education and contact facts exactly;
7. writes a simple one-column `.docx`;
8. writes an optional JSON report showing selected bullet IDs, scores, skill gaps and top qualification lines;
9. audits the generated DOCX for hidden-text, comments and watermark-like XML constructs.

It does **not** call a generative-AI API and does **not** rewrite or invent accomplishment bullets.

## Privacy

This repository is public. Keep your real files only in the already ignored folders:

```text
resume_private/
jd_private/
tailored_resumes/
```

Do not commit your real master JSON or generated applications.

## 1. Create your private master fact bank

Copy the public example:

```bash
mkdir -p resume_private jd_private tailored_resumes
cp resume_master_schema.example.json resume_private/master_resume.json
```

Then replace the example content with your real facts.

### Locked facts

Every experience, project and education entry must contain:

```json
"locked": true
```

The builder will refuse the master file if one of those core entries is not locked.

### Verified bullet bank

Store multiple truthful bullets under each experience/project. The builder chooses among them but never changes their wording.

```json
{
  "id": "exp1-b3",
  "text": "Automated repeatable Azure infrastructure tasks using PowerShell.",
  "skills": ["Microsoft Azure", "PowerShell"],
  "keywords": ["cloud infrastructure", "automation"],
  "verified": true
}
```

If a bullet is experimental, inaccurate or not interview-defensible, leave:

```json
"verified": false
```

It will never be rendered.

## 2. Update your verified skill inventory

`resume_skill_inventory.json` controls which JD skills may appear in the tailored Skills section.

Only set `verified: true` when you can support the skill with real work, coursework, certification or project experience.

The tool never fills the 15-skill limit with unverified keywords. If only eight verified JD skills match, it outputs eight and reports the rest as gaps.

## 3. Build from copied JD text

Save the description:

```text
jd_private/capital-one-software-engineer.txt
```

Run:

```bash
python resume_builder.py \
  --master resume_private/master_resume.json \
  --jd jd_private/capital-one-software-engineer.txt \
  --out tailored_resumes/capital-one-software-engineer.docx \
  --report tailored_resumes/capital-one-software-engineer.match.json
```

## 4. Or build from a public job URL

For server-rendered job pages:

```bash
python resume_builder.py \
  --master resume_private/master_resume.json \
  --jd-url "https://company.example/jobs/123" \
  --out tailored_resumes/company-role.docx \
  --report tailored_resumes/company-role.match.json
```

Some Workday/JavaScript-heavy pages may not expose the full JD to a simple HTTP request. If URL mode reports too little readable text, copy the JD into `jd_private/` and use `--jd` instead.

## Selection rules

### Experience

All locked experience entries remain on the resume. For each role, the builder selects up to four verified bullets by default. Matching uses:

- explicitly tagged skills that appear in the JD;
- explicit bullet keywords/phrases that appear in the JD;
- a small deterministic text-overlap signal.

If an older role has no JD overlap, one verified bullet is retained by default so the employer/date history does not disappear.

### Projects

Projects are optional and are ranked by the same truthful evidence. By default, at most three matching projects are included.

### Skills

Up to 15 skills are selected from `resume_skill_inventory.json`, and only skills with `verified: true` are eligible.

### Gaps

Requested but unverified inventory skills appear only in the JSON report under `requested_but_unverified`. They are never inserted into the DOCX.

## ATS-safe DOCX choices

The generated document intentionally uses:

- one column;
- Arial text;
- ordinary paragraphs;
- no tables;
- no text boxes;
- no headers/footers for important information;
- no invisible/white keyword stuffing;
- no comments;
- no generated graphics;
- no hidden text;
- no watermark object added by this tool.

Editor metadata such as author/last-modified-by is blanked before saving.

The output is still a normal DOCX file, so Word or another editor can add normal document metadata later if you edit and resave it.

## Match report

The optional `.match.json` makes the process auditable. It contains:

- SHA-256 fingerprint of locked identity/date facts;
- selected verified skills;
- requested but unverified skills;
- ranked JD skills;
- top qualification lines;
- selected experience bullet IDs and scoring evidence;
- selected project IDs/bullets and scoring evidence;
- DOCX hidden-text/watermark audit result.

This makes it easy to verify that tailoring only selected existing evidence rather than inventing new experience.

## Tuning length

Defaults are designed for a compact technical resume. They can be changed per application:

```bash
python resume_builder.py \
  --master resume_private/master_resume.json \
  --jd jd_private/job.txt \
  --out tailored_resumes/job.docx \
  --max-skills 15 \
  --max-exp-bullets 3 \
  --max-projects 2 \
  --max-project-bullets 2
```

For most early-career applications, keep the output concise and only include bullets you can discuss confidently in an interview.
