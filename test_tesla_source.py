import unittest
from unittest.mock import patch

import pandas as pd

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

    def test_install_routes_tesla_company_row_to_adapter(self):
        original_scrape_company = js.scrape_company
        original_scrape_tesla = js.scrape_tesla
        had_flag = getattr(js, "_tesla_adapter_installed", False)
        if had_flag:
            delattr(js, "_tesla_adapter_installed")
        try:
            ts.install()
            row = pd.Series({
                "company": "Tesla",
                "platform": "tesla",
                "careers_url": "https://www.tesla.com/careers",
                "official_url": "https://www.tesla.com/careers",
            })
            with patch.object(ts, "scrape_tesla") as mocked:
                js.scrape_company(row)
                mocked.assert_called_once_with(
                    "https://www.tesla.com/careers",
                    "Tesla",
                    "https://www.tesla.com/careers",
                )
        finally:
            js.scrape_company = original_scrape_company
            js.scrape_tesla = original_scrape_tesla
            if had_flag:
                js._tesla_adapter_installed = True
            elif hasattr(js, "_tesla_adapter_installed"):
                delattr(js, "_tesla_adapter_installed")


if __name__ == "__main__":
    unittest.main()
