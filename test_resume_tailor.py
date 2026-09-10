import unittest

from resume_tailor import load_inventory, rank_jd_skills, replace_skills_section, tailor_resume


INVENTORY = [
    {"name": "Python", "aliases": ["Python"], "verified": True},
    {"name": "SQL", "aliases": ["SQL"], "verified": True},
    {"name": "Microsoft Azure", "aliases": ["Azure", "Microsoft Azure"], "verified": True},
    {"name": "AWS", "aliases": ["AWS", "Amazon Web Services"], "verified": False},
    {"name": "Terraform", "aliases": ["Terraform"], "verified": False},
]


class ResumeTailorTests(unittest.TestCase):
    def test_rank_prioritizes_requirement_lines(self):
        jd = """
        Python is used by the team.
        Minimum qualifications: SQL and SQL experience required.
        Preferred: Azure.
        """
        ranked = rank_jd_skills(jd, INVENTORY)
        names = [item["name"] for item in ranked]
        self.assertEqual("SQL", names[0])
        self.assertIn("Microsoft Azure", names)

    def test_only_verified_skills_are_inserted(self):
        resume = """HARSH\n\nSKILLS\nOld Skill\n\nEXPERIENCE\n- Built systems.\n"""
        jd = "Required: Python, SQL, AWS, and Terraform."
        tailored, report = tailor_resume(resume, jd, INVENTORY, max_skills=15)
        self.assertIn("Python, SQL", tailored)
        self.assertNotIn("AWS,", tailored)
        self.assertNotIn("Terraform", tailored.split("EXPERIENCE")[0])
        self.assertEqual(["AWS", "Terraform"], report["requested_but_unverified"])

    def test_does_not_borrow_unverified_skill_to_fill_15(self):
        resume = "## Skills\nOld Skill\n\n## Experience\nExample\n"
        jd = "Python SQL AWS Terraform"
        tailored, report = tailor_resume(resume, jd, INVENTORY, max_skills=15)
        self.assertEqual(["Python", "SQL"], report["selected_verified_skills"])
        self.assertIn("Python, SQL", tailored)

    def test_replace_skills_preserves_other_sections(self):
        resume = "## Summary\nData professional\n\n## Skills\nOld Skill\n\n## Experience\n- Kept exactly\n"
        updated = replace_skills_section(resume, ["Python", "SQL"])
        self.assertIn("## Skills\nPython, SQL", updated)
        self.assertIn("## Experience\n- Kept exactly", updated)

    def test_skill_alias_uses_safe_boundaries(self):
        inventory = [
            {"name": "Go", "aliases": ["Go"], "verified": True},
            {"name": "C++", "aliases": ["C++"], "verified": True},
        ]
        ranked = rank_jd_skills("We use Google Cloud and C++.", inventory)
        names = [item["name"] for item in ranked]
        self.assertNotIn("Go", names)
        self.assertIn("C++", names)

    def test_real_inventory_matches_documented_resume_stack(self):
        skills = {item["name"]: item["verified"] for item in load_inventory()}
        documented = [
            "AWS",
            "Terraform",
            "Kubernetes",
            "Apache Airflow",
            "dbt",
            "Kafka",
            "JavaScript",
            "Supabase",
            "BigQuery",
            "Excel",
            "GitHub Actions",
        ]
        for name in documented:
            self.assertTrue(skills[name], name)

        cautious = ["Google Cloud Platform", "Databricks", "Snowflake", "Java", "Cassandra"]
        for name in cautious:
            self.assertFalse(skills[name], name)


if __name__ == "__main__":
    unittest.main()
