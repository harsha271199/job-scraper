import unittest

from official_sources import (
    parse_color_health_jobs,
    parse_google_company_jobs,
    parse_kula_jobs,
    parse_snap_jobs,
)


class OfficialSourceTests(unittest.TestCase):
    def test_parse_snap_jobs(self):
        html = """
        <table>
          <tr><th>Role</th><th>Team</th><th>Type</th><th>Location</th></tr>
          <tr>
            <td><a href="/job?id=Q326SWEML1">Machine Learning Engineer, Level 3</a></td>
            <td>Engineering</td><td>Regular</td><td>Bellevue; Palo Alto; Seattle</td>
          </tr>
          <tr>
            <td><a href="https://careers.snap.com/job?id=Q999">Data Scientist, Level 4</a></td>
            <td>Growth</td><td>Regular</td><td>Los Angeles; New York</td>
          </tr>
        </table>
        """
        jobs = list(parse_snap_jobs(html))
        self.assertEqual(2, len(jobs))
        self.assertEqual("Machine Learning Engineer, Level 3", jobs[0]["title"])
        self.assertEqual("Bellevue; Palo Alto; Seattle", jobs[0]["location"])
        self.assertEqual("https://careers.snap.com/job?id=Q326SWEML1", jobs[0]["link"])
        self.assertEqual("Regular", jobs[0]["job_type"])

    def test_ignores_non_job_links_and_duplicates(self):
        html = """
        <a href="/jobs">View openings</a>
        <a href="https://example.com/job?id=BAD">Software Engineer</a>
        <a href="/job?id=ONE">Software Engineer, Level 3</a>
        <a href="/job?id=ONE">Software Engineer, Level 3</a>
        """
        jobs = list(parse_snap_jobs(html))
        self.assertEqual(1, len(jobs))
        self.assertEqual("https://careers.snap.com/job?id=ONE", jobs[0]["link"])

    def test_parse_kula_jobs(self):
        html = """
        <section>
          <div class="job-card">
            <div>Engineering</div>
            <div>Software Engineer, New Grad 2027</div>
            <div>Pleasanton, California, United States</div>
            <a href="/10xgenomics/48910">Apply Now</a>
          </div>
          <div class="job-card">
            <div>Marketing</div>
            <div>Staff Data Scientist, Sales Analytics</div>
            <div>Pleasanton, California, United States</div>
            <a href="/10xgenomics/48911">Apply Now</a>
          </div>
        </section>
        """
        jobs = list(parse_kula_jobs(html))
        self.assertEqual(2, len(jobs))
        self.assertEqual("Software Engineer, New Grad 2027", jobs[0]["title"])
        self.assertEqual("Pleasanton, California, United States", jobs[0]["location"])
        self.assertEqual("https://careers.kula.ai/10xgenomics/48910", jobs[0]["link"])

    def test_parse_google_company_jobs(self):
        html = """
        <div class="job-card">
          <a href="/about/careers/applications/jobs/results/123456789012345678-software-engineer">
            Software Engineer, DeepMind
          </a>
          <span>Mountain View, CA, USA</span>
        </div>
        <a href="/about/careers/applications/jobs/results">Job search</a>
        """
        jobs = list(parse_google_company_jobs(html))
        self.assertEqual(1, len(jobs))
        self.assertEqual("Software Engineer, DeepMind", jobs[0]["title"])
        self.assertEqual("Mountain View, CA, USA", jobs[0]["location"])

    def test_parse_color_health_jobs(self):
        html = """
        <div class="role">
          <a href="https://app.careerpuck.com/job-board/color-health/job/abc123">
            <span>South San Francisco, California</span>
            <span>Software Engineer, New Grad 2026</span>
            <span>About this role</span>
          </a>
        </div>
        """
        jobs = list(parse_color_health_jobs(html))
        self.assertEqual(1, len(jobs))
        self.assertEqual("Software Engineer, New Grad 2026", jobs[0]["title"])
        self.assertEqual("South San Francisco, California", jobs[0]["location"])
        self.assertIn("app.careerpuck.com", jobs[0]["link"])


if __name__ == "__main__":
    unittest.main()
