"""Production entrypoint: install official-site adapters, then run the core scraper."""

import job_scraper as js
from official_sources import install


if __name__ == "__main__":
    install()
    js.main()
