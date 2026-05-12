import logging
import re
from datetime import datetime
from datetime import timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup
from nxd.core.context import Snowflake
from nxd.data_product.context import API
from snowflake.connector import connect

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)

_MAX_PAGES = 20
_CATEGORIES = ["apparel", "consumables", "household"]


def _parse_price(text: str) -> float | None:
    # Listing pages render price as a plain number (e.g. "24.99"), no $ sign.
    text = text.strip()
    try:
        return float(text) if text else None
    except ValueError:
        return None


def _scrape_listing_page(
    session: requests.Session,
    base_url: str,
    category: str,
    page: int,
) -> list[dict]:
    """Scrape one paginated listing page for a given category.

    The catalog renders each product as a ``div.row.product`` containing:
    - ``div.description h3 a`` — product name + absolute URL
    - ``div.price-wrap div.price`` — plain numeric price (e.g. ``24.99``)
    """
    resp = session.get(
        f"{base_url}/products",
        params={"category": category, "page": page},
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    products = []

    for card in soup.select("div.row.product"):
        link = card.select_one("div.description h3 a")
        if not link:
            continue

        href = link.get("href", "")
        # href is an absolute URL: https://web-scraping.dev/product/1
        product_id = href.rstrip("/").split("/")[-1]
        name = link.get_text(strip=True)

        # Price is a plain number inside div.price (no $ prefix)
        price_div = card.select_one("div.price-wrap div.price")
        price_text = price_div.get_text(strip=True) if price_div else ""

        products.append(
            {
                "product_id": product_id,
                "name": name,
                "product_url": href,
                "price_text": price_text,
            }
        )

    return products


def _scrape_product_detail(session: requests.Session, product_url: str) -> dict:
    """Scrape a product detail page to extract description, brand, and original price.

    The detail page structure:
    - Description paragraph follows an h3/h4 labelled "Description".
    - Brand is a row in the "Features" table with the key "brand".
    - Original price appears as "from $N.NN" when a discount is active.
    """
    resp = session.get(product_url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Description ----------------------------------------------------------------
    description = ""
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "description" in heading.get_text(strip=True).lower():
            para = heading.find_next("p")
            if para:
                description = para.get_text(strip=True)
            break

    # Brand (from features table) ------------------------------------------------
    brand = ""
    for row in soup.select("table tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2 and cells[0].get_text(strip=True).lower() == "brand":
            brand = cells[1].get_text(strip=True)
            break

    # Original price (pre-discount) ----------------------------------------------
    original_price = None
    for node in soup.find_all(string=re.compile(r"from\s+\$\d")):
        match = re.search(r"from\s+\$(\d+(?:\.\d{2})?)", node)
        if match:
            original_price = float(match.group(1))
        break

    return {"description": description, "brand": brand, "original_price": original_price}


def scrape_catalog(base_url: str) -> pd.DataFrame:
    """Scrape the full product catalog and return an enriched DataFrame.

    Iterates over all categories and pages, collecting product stubs from the
    listing pages and enriching each with detail-page data (description, brand,
    original price). No external storage is written.

    Args:
        base_url: Root URL of the catalog site (e.g. ``https://web-scraping.dev``).

    Returns:
        A :class:`pandas.DataFrame` with one row per unique product.
    """
    base_url = base_url.rstrip("/")
    _logger.info("Starting web catalog scrape from %s", base_url)

    session = requests.Session()
    session.headers.update({"User-Agent": "NextData-Catalog-Scraper/1.0"})

    scraped_at = datetime.now(tz=timezone.utc)
    seen_ids: set[str] = set()
    stubs: list[dict] = []

    # Scrape listing pages per category to capture category per product ----------
    for category in _CATEGORIES:
        _logger.info("Scraping category: %s", category)
        for page in range(1, _MAX_PAGES + 1):
            page_products = _scrape_listing_page(session, base_url, category, page)
            new_products = [p for p in page_products if p["product_id"] not in seen_ids]
            if not new_products:
                break
            for product in new_products:
                product["category"] = category.capitalize()
                seen_ids.add(product["product_id"])
            stubs.extend(new_products)

    _logger.info(
        "Collected %d unique products across %d categories",
        len(stubs),
        len(_CATEGORIES),
    )

    # Enrich each product with detail-page data ----------------------------------
    rows: list[dict] = []
    for stub in stubs:
        try:
            detail = _scrape_product_detail(session, stub["product_url"])
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "Failed to scrape detail for product %s: %s",
                stub["product_id"],
                exc,
            )
            detail = {"description": "", "brand": "", "original_price": None}

        rows.append(
            {
                "product_id": stub["product_id"],
                "name": stub["name"],
                "category": stub["category"],
                "price": _parse_price(stub.get("price_text", "")),
                "original_price": detail["original_price"],
                "description": detail["description"],
                "brand": detail["brand"],
                "product_url": stub["product_url"],
                "scraped_at": scraped_at,
            }
        )

    df = pd.DataFrame(rows)
    _logger.info("Scraped %d enriched product records", len(df))
    return df


def transform(catalog_source: API, snowflake: Snowflake) -> None:
    df = scrape_catalog(catalog_source.url)
    _logger.info("Writing %d product records to Snowflake", len(df))

    # Write to Snowflake ---------------------------------------------------------
    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()

    # cursor.execute(
    #     """
    #     CREATE TABLE IF NOT EXISTS CATALOG_PRODUCTS (
    #         product_id     VARCHAR,
    #         name           VARCHAR,
    #         category       VARCHAR,
    #         price          NUMBER(8, 2),
    #         original_price NUMBER(8, 2),
    #         description    VARCHAR,
    #         brand          VARCHAR,
    #         product_url    VARCHAR,
    #         scraped_at     TIMESTAMP_NTZ
    #     )
    #     """
    # )
    cursor.execute("TRUNCATE TABLE CATALOG_PRODUCTS")

    cursor.executemany(
        """
        INSERT INTO CATALOG_PRODUCTS
            (product_id, name, category, price, original_price, description, brand, product_url, scraped_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::TIMESTAMP_NTZ)
        """,
        [
            (
                row["product_id"],
                row["name"],
                row["category"],
                row["price"],
                row["original_price"],
                row["description"],
                row["brand"],
                row["product_url"],
                row["scraped_at"].isoformat() if pd.notna(row["scraped_at"]) else None,
            )
            for _, row in df.iterrows()
        ],
    )
    conn.commit()
    conn.close()

    _logger.info("Successfully loaded %d catalog products into Snowflake", len(df))
