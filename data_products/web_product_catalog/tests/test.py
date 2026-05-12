"""Local runner for the web-product-catalog scraper.

Runs the scraping logic from :func:`transform.scrape_catalog` without any
Snowflake IO, printing a summary and optionally saving to a CSV file.

Usage::

    python main.py                                       # default URL
    python main.py https://web-scraping.dev              # custom URL
    python main.py https://web-scraping.dev out.csv      # save to CSV
"""

import logging
import sys

sys.path.append("../")

from transform import scrape_catalog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

_DEFAULT_URL = "https://web-scraping.dev"


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_URL
    csv_path = sys.argv[2] if len(sys.argv) > 2 else None

    df = scrape_catalog(url)

    print(f"\n{'=' * 60}")
    print(f"Scraped {len(df)} products from {url}")
    print(f"{'=' * 60}")
    print(df.to_string(index=False, max_colwidth=60))

    if csv_path:
        df.to_csv(csv_path, index=False)
        print(f"\nSaved to {csv_path}")


if __name__ == "__main__":
    main()
