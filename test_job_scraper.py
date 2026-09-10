import unittest

import job_scraper as js


class JobScraperTests(unittest.TestCase):
    def setUp(self):
        js.results.clear()
        js.old_links.clear()
        js.error_messages.clear()

    def test_keyword_match(self):
        self.assertTrue(js.keyword_match("Software Engineer, New Grad 2027"))
        self.assertTrue(js.keyword_match("Data Scientist"))
        self.assertFalse(js.keyword_match("Senior Software Engineer"))
        self.assertFalse(js.keyword_match("Embedded Software Engineer"))
        self.assertFalse(js.keyword_match("Account Executive"))

    def test_us_location(self):
        self.assertTrue(js.is_us_location("Remote - USA"))
        self.assertTrue(js.is_us_location("San Francisco, CA"))
        self.assertTrue(js.is_us_location("Cupertino"))
        self.assertFalse(js.is_us_location("Remote, United Kingdom"))
        self.assertFalse(js.is_us_location("Remote - Canada"))
        self.assertFalse(js.is_us_location("Remote"))
        self.assertFalse(js.is_us_location("N/A"))

    def test_add_result_dedupes(self):
        self.assertTrue(
            js.add_result(
                "TestCo",
                "Software Engineer",
                "Phoenix, AZ",
                "https://test.example/jobs/1",
                official_url="https://test.example/careers",
            )
        )
        self.assertFalse(
            js.add_result(
                "TestCo",
                "Software Engineer",
                "Phoenix, AZ",
                "https://test.example/jobs/1",
                official_url="https://test.example/careers",
            )
        )
        self.assertEqual(1, len(js.results))

    def test_strip_repeated_headers(self):
        old = """# 📢 Job Listings for Harsha — September 09, 2026
> Updated every hour. Newest batch first.
### 🕐 Batch at one
x
# 📢 Job Listings for Harsha — September 09, 2026
> Updated every hour. Newest batch first.
### 🕐 Batch at two
y
"""
        cleaned = js._strip_repeated_headers(old)
        self.assertNotIn("# 📢 Job Listings", cleaned)
        self.assertNotIn("> Updated every hour.", cleaned)
        self.assertIn("Batch at one", cleaned)
        self.assertIn("Batch at two", cleaned)

    def test_candidate_schema_org(self):
        obj = {
            "@type": "JobPosting",
            "title": "Machine Learning Engineer",
            "jobLocation": {
                "address": {
                    "addressLocality": "Sunnyvale",
                    "addressRegion": "CA",
                    "addressCountry": "US",
                }
            },
            "url": "https://careers.example.com/jobs/123",
            "datePosted": "2026-09-09",
        }
        got = js._candidate_from_json(
            obj, "https://careers.example.com/", "Example"
        )
        self.assertIsNotNone(got)
        title, location, link, posted = got
        self.assertEqual("Machine Learning Engineer", title)
        self.assertIn("Sunnyvale", location)
        self.assertEqual("https://careers.example.com/jobs/123", link)
        self.assertEqual("2026-09-09", posted)

    def test_tesla_recursive_list_detection_shape(self):
        sample = {
            "lookup": {
                "locations": {
                    "1": "Palo Alto, California",
                    "2": "Toronto, Ontario",
                }
            },
            "payload": {
                "positions": [
                    {"id": "100", "t": "Software Engineer", "l": "1"},
                    {"id": "101", "t": "Software Engineer", "l": "2"},
                ]
            },
        }
        lists = []
        for obj in js._walk_json(sample):
            for value in obj.values():
                if (
                    isinstance(value, list)
                    and value
                    and isinstance(value[0], dict)
                    and {"id", "t", "l"}.issubset(value[0].keys())
                ):
                    lists.append(value)
        self.assertEqual(1, len(lists))
        self.assertTrue(js.is_us_location(sample["lookup"]["locations"]["1"]))
        self.assertFalse(js.is_us_location(sample["lookup"]["locations"]["2"]))


if __name__ == "__main__":
    unittest.main()
