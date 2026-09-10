import unittest

from official_sources import parse_snap_jobs


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


if __name__ == "__main__":
    unittest.main()
