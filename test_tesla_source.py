import unittest

import job_scraper as js
import tesla_source as ts


class TeslaSourceTests(unittest.TestCase):
    def setUp(self):
        js.results.clear()
        js.old_links.clear()
        js.error_messages.clear()

    def test_iter_postings_finds_jobs_even_when_list_starts_with_non_job(self):
        sample = {
            "lookup": {"locations": {"20899": "Palo Alto, California"}},
            "payload": {
                "mixed": [
                    {"kind": "metadata"},
                    {"id": "280079", "t": "Data Engineer, DesignX", "l": "20899"},
                ]
            },
        }
        jobs = list(ts.iter_tesla_postings(sample))
        self.assertEqual(1, len(jobs))
        self.assertEqual("280079", jobs[0]["id"])

    def test_tesla_job_url_uses_current_slug_format(self):
        self.assertEqual(
            "https://www.tesla.com/careers/search/job/data-engineer-designx-280079",
            ts.tesla_job_url("Data Engineer, DesignX", "280079"),
        )


if __name__ == "__main__":
    unittest.main()
