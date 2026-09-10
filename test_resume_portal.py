import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import resume_portal_feed as rp


class ResumePortalFeedTests(unittest.TestCase):
    def test_job_id_is_stable_and_short(self):
        a = rp.job_id("https://example.com/job/123")
        b = rp.job_id("https://example.com/job/123")
        self.assertEqual(a, b)
        self.assertEqual(16, len(a))

    def test_profile_classification(self):
        self.assertEqual("data-engineering", rp.classify_profile("Data Engineer II"))
        self.assertEqual("software-engineering", rp.classify_profile("Software Engineer"))
        self.assertEqual("cloud-devops", rp.classify_profile("Site Reliability Engineer"))
        self.assertEqual("machine-learning", rp.classify_profile("Machine Learning Engineer"))
        self.assertEqual("data-analytics", rp.classify_profile("Data Analyst"))
        self.assertEqual(
            "data-engineering",
            rp.classify_profile("Data Engineer", ["Machine Learning", "Python"]),
        )

    def test_detect_skills_uses_inventory_aliases(self):
        inventory = [
            {"name": "AWS", "aliases": ["Amazon Web Services"], "verified": True},
            {"name": "Python", "aliases": [], "verified": True},
            {"name": "Go", "aliases": ["Golang"], "verified": False},
        ]
        skills = rp.detect_skills("Python on Amazon Web Services. Python pipelines.", inventory)
        self.assertEqual(["Python", "AWS"], skills)

    def test_portal_live_check_requires_expected_page(self):
        response = Mock(ok=True, text="Resume + Apply — Private Master Resume")
        with patch.object(rp.requests, "get", return_value=response):
            rp._portal_live_cache = None
            self.assertTrue(rp.portal_is_live(force=True))

        response = Mock(ok=True, text="Some unrelated page")
        with patch.object(rp.requests, "get", return_value=response):
            rp._portal_live_cache = None
            self.assertFalse(rp.portal_is_live(force=True))

    def test_prepare_does_not_mutate_real_apply_link(self):
        jobs = [{
            "company": "Example",
            "title": "Data Engineer",
            "location": "Phoenix, AZ",
            "link": "https://example.com/job/123",
            "official_url": "https://example.com/careers",
            "posted": "Today",
        }]
        fake_jd = (
            "Minimum qualifications: Python experience required. "
            "Build reliable Python data pipelines and production data platforms. "
            "Work with engineering teams on scalable analytics systems."
        )
        with tempfile.TemporaryDirectory() as td:
            feed_path = Path(td) / "job_signals.json"
            inv_path = Path(td) / "resume_skill_inventory.json"
            inv_path.write_text(json.dumps({"skills": [{"name": "Python", "aliases": [], "verified": True}]}))
            with patch.object(rp, "FEED_PATH", feed_path), \
                 patch.object(rp, "INVENTORY_PATH", inv_path), \
                 patch.object(rp, "_visible_page_text", return_value=fake_jd), \
                 patch.object(rp, "portal_is_live", return_value=True):
                public = rp.prepare_portal_jobs(jobs)

            self.assertEqual("https://example.com/job/123", jobs[0]["link"])
            self.assertIn("harsha271199.github.io/job-scraper", public[0]["link"])
            data = json.loads(feed_path.read_text())
            record = next(iter(data["jobs"].values()))
            self.assertEqual("https://example.com/job/123", record["apply_url"])
            self.assertIn("Python", record["detected_skills"])
            self.assertIn("Python", record["verified_skills"])
            self.assertEqual([], record["unverified_skills"])
            self.assertTrue(data["portal_live"])

    def test_prepare_keeps_direct_apply_link_when_portal_is_offline(self):
        jobs = [{
            "company": "Example",
            "title": "Software Engineer",
            "location": "Tempe, AZ",
            "link": "https://example.com/job/456",
            "official_url": "https://example.com/careers",
            "posted": "Today",
        }]
        with tempfile.TemporaryDirectory() as td:
            feed_path = Path(td) / "job_signals.json"
            inv_path = Path(td) / "resume_skill_inventory.json"
            inv_path.write_text(json.dumps({"skills": []}))
            with patch.object(rp, "FEED_PATH", feed_path), \
                 patch.object(rp, "INVENTORY_PATH", inv_path), \
                 patch.object(rp, "_visible_page_text", return_value=""), \
                 patch.object(rp, "portal_is_live", return_value=False):
                public = rp.prepare_portal_jobs(jobs)

            self.assertEqual("https://example.com/job/456", public[0]["link"])
            data = json.loads(feed_path.read_text())
            self.assertFalse(data["portal_live"])
            record = next(iter(data["jobs"].values()))
            self.assertEqual("https://example.com/job/456", record["apply_url"])

    def test_public_feed_contains_no_resume_private_data(self):
        record = rp.build_record({
            "company": "Example",
            "title": "Software Engineer",
            "location": "Tempe, AZ",
            "link": "",
            "official_url": "",
            "posted": "N/A",
        }, inventory=[])
        serialized = json.dumps(record).casefold()
        self.assertNotIn("harshabalraj99", serialized)
        self.assertNotIn("623-341-9706", serialized)

    def test_portal_source_has_no_private_resume_or_ai_api(self):
        html = Path("portal/index.html").read_text(encoding="utf-8")
        js = Path("portal/app.js").read_text(encoding="utf-8")
        source = (html + js).casefold()
        self.assertNotIn("harshabalraj99", source)
        self.assertNotIn("623-341-9706", source)
        self.assertNotIn("api.openai.com", source)
        self.assertIn("localstorage", source)


if __name__ == "__main__":
    unittest.main()
