import tempfile
import unittest
from pathlib import Path

from docx import Document

from resume_builder import (
    audit_docx,
    build_selection,
    export_docx,
    extract_top_qualification_lines,
    validate_master,
)


INVENTORY = [
    {"name": "Python", "aliases": ["Python"], "verified": True},
    {"name": "SQL", "aliases": ["SQL"], "verified": True},
    {"name": "Microsoft Azure", "aliases": ["Azure", "Microsoft Azure"], "verified": True},
    {"name": "Docker", "aliases": ["Docker", "containers"], "verified": True},
    {"name": "AWS", "aliases": ["AWS", "Amazon Web Services"], "verified": False},
]


def sample_master():
    return {
        "contact": {
            "name": "Example Candidate",
            "headline": "Data and Cloud Engineer",
            "email": "candidate@example.com",
            "phone": "555-111-2222",
            "location": "Tempe, AZ",
            "links": ["https://example.com/profile"],
        },
        "summary": "Engineer focused on data and cloud systems.",
        "experience": [
            {
                "id": "exp-1",
                "company": "Example Cloud Co",
                "title": "Cloud Engineer",
                "location": "Tempe, AZ",
                "start": "May 2022",
                "end": "Nov 2024",
                "locked": True,
                "bullets": [
                    {
                        "id": "exp-1-azure",
                        "text": "Automated Azure infrastructure operations using PowerShell and repeatable runbooks.",
                        "skills": ["Microsoft Azure"],
                        "keywords": ["cloud infrastructure", "automation"],
                        "verified": True,
                    },
                    {
                        "id": "exp-1-unrelated",
                        "text": "Documented internal support processes for end users.",
                        "skills": [],
                        "keywords": ["support documentation"],
                        "verified": True,
                    },
                    {
                        "id": "exp-1-fake",
                        "text": "Managed a large AWS Kubernetes platform.",
                        "skills": ["AWS"],
                        "keywords": ["kubernetes"],
                        "verified": False,
                    },
                ],
            }
        ],
        "projects": [
            {
                "id": "project-python",
                "name": "Analytics Pipeline",
                "subtitle": "Data project",
                "locked": True,
                "bullets": [
                    {
                        "id": "project-python-b1",
                        "text": "Built a Python and SQL data pipeline for repeatable analytics processing.",
                        "skills": ["Python", "SQL"],
                        "keywords": ["data pipeline"],
                        "verified": True,
                    }
                ],
            },
            {
                "id": "project-design",
                "name": "Design Portfolio",
                "subtitle": "Mechanical project",
                "locked": True,
                "bullets": [
                    {
                        "id": "project-design-b1",
                        "text": "Created mechanical drawings for a design exercise.",
                        "skills": [],
                        "keywords": ["mechanical drawing"],
                        "verified": True,
                    }
                ],
            },
        ],
        "education": [
            {
                "school": "Example University",
                "degree": "MS Data Science",
                "location": "Tempe, AZ",
                "start": "Jan 2025",
                "end": "Dec 2026",
                "details": [],
                "locked": True,
            }
        ],
        "certifications": ["Cloud Certification"],
        "base_skills": ["Python", "SQL", "Microsoft Azure"],
    }


class ResumeBuilderTests(unittest.TestCase):
    def test_requires_locked_core_entries(self):
        master = sample_master()
        master["experience"][0]["locked"] = False
        with self.assertRaises(ValueError):
            validate_master(master)

    def test_selects_verified_relevant_bullets_without_rewriting(self):
        master = sample_master()
        jd = """
        Basic qualifications: experience with Azure cloud infrastructure and automation.
        Required: Python and SQL for data pipelines.
        Preferred: AWS.
        """
        selection = build_selection(master, jd, INVENTORY, max_projects=2)
        exp = selection["experience"][0]
        selected_texts = [item["text"] for item in exp["bullets"]]
        self.assertIn(
            "Automated Azure infrastructure operations using PowerShell and repeatable runbooks.",
            selected_texts,
        )
        self.assertNotIn("Managed a large AWS Kubernetes platform.", selected_texts)
        self.assertEqual(
            "Automated Azure infrastructure operations using PowerShell and repeatable runbooks.",
            exp["bullets"][0]["text"],
        )
        self.assertIn("AWS", selection["requested_but_unverified"])

    def test_selects_relevant_project(self):
        master = sample_master()
        jd = "Required: Python SQL data pipeline experience."
        selection = build_selection(master, jd, INVENTORY, max_projects=1)
        self.assertEqual(1, len(selection["projects"]))
        self.assertEqual("project-python", selection["projects"][0]["entry"]["id"])

    def test_extracts_qualification_lines(self):
        jd = """
        About us: We build software.
        Minimum qualifications: 2+ years of experience with Python and SQL.
        Preferred qualifications: experience with Azure.
        """
        lines = extract_top_qualification_lines(jd)
        self.assertTrue(lines)
        self.assertIn("Minimum qualifications", lines[0]["text"])

    def test_exports_text_only_docx_and_passes_audit(self):
        master = sample_master()
        jd = "Required: Python, SQL, Azure cloud infrastructure and automation. Preferred: AWS."
        selection = build_selection(master, jd, INVENTORY, max_projects=1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "resume.docx"
            export_docx(master, selection, path)
            self.assertTrue(path.exists())
            audit = audit_docx(path)
            self.assertTrue(audit["clean"], audit)

            doc = Document(path)
            text = "\n".join(p.text for p in doc.paragraphs)
            self.assertIn("Example Candidate", text)
            self.assertIn("Example Cloud Co | Cloud Engineer", text)
            self.assertIn("May 2022 - Nov 2024", text)
            self.assertIn("Python", text)
            self.assertIn("SQL", text)
            self.assertNotIn("Managed a large AWS Kubernetes platform.", text)

            props = doc.core_properties
            self.assertEqual("", props.author)
            self.assertEqual("", props.last_modified_by)


if __name__ == "__main__":
    unittest.main()
