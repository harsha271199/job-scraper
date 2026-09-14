"""Production entrypoint: clean migrations, install adapters, run scraper."""

import job_scraper as js
from cleanup_opendoor_batch import cleanup
from official_sources import install
from resume_portal_feed import install as install_resume_portal
from tesla_source import install as install_tesla_source


if __name__ == "__main__":
    if cleanup():
        print("Cleaned malformed Opendoor batch and reset its seen links")
    install_tesla_source()
    install()
    install_resume_portal(js)
    js.main()
