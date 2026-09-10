# ATS Resume Tailor

This repository includes a deterministic resume-skill tailoring helper for job applications.

## Why this exists

Many recruiting systems parse resumes and compare the candidate's stated qualifications against a job requisition. This helper improves keyword alignment without fabricating experience.

It deliberately **does not call a generative-AI API** and it does **not** add hidden text, white text, comments, tracking pixels, images, or watermarks.

## Privacy first

This repository is public. Do **not** commit your real resume, personal contact details, or copied job descriptions.

Keep private inputs in the ignored folders:

- `resume_private/`
- `jd_private/`
- `tailored_resumes/`

## How it works

1. `resume_skill_inventory.json` stores canonical skills and aliases.
2. Every skill has `verified: true` or `verified: false`.
3. The script scans the job description and ranks matching skills.
4. Up to 15 verified JD skills are placed in the resume's Skills section.
5. JD skills marked unverified are **not** inserted. They are reported as gaps for you to review.
6. The remainder of the resume is preserved verbatim.

This prevents a common bad practice: copying every JD keyword into the resume even when the candidate has never used that skill.

## Usage

Create private local files:

```text
resume_private/base_resume.md
jd_private/job.txt
```

The resume may use either a Markdown heading such as `## Skills` or a plain-text `SKILLS` section.

Run:

```bash
python resume_tailor.py \
  --resume resume_private/base_resume.md \
  --jd jd_private/job.txt \
  --out tailored_resumes/company-role.md \
  --report tailored_resumes/company-role-match.json
```

The JSON report contains:

- selected verified skills
- requested but unverified skills
- ranked JD skill evidence
- occurrence/priority scores

## Example

If a JD strongly requests:

```text
Python, SQL, Azure, AWS, Terraform
```

and the inventory marks Python, SQL, and Azure verified but AWS and Terraform unverified, the output Skills section will contain only:

```text
Python, SQL, Microsoft Azure
```

The report will list AWS and Terraform under `requested_but_unverified`.

## Updating your verified inventory

Change a skill to `verified: true` only when you can truthfully support it in an interview or with work/project experience.

You can add aliases to match employer wording, for example:

```json
{"name": "Microsoft Azure", "aliases": ["Azure", "Azure Cloud"], "verified": true}
```

## ATS formatting guidance

Keep the submitted resume simple:

- one column
- normal section headings
- text-based PDF or DOCX
- no charts/icons for important information
- no critical content in headers/footers
- no white/invisible keyword stuffing
- use the employer's terminology when it accurately describes your experience

The skill tailor is only one part of matching. Basic qualifications such as years of experience, degree requirements, work authorization, location, and role-specific experience still matter.
