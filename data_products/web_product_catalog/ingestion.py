import logging
import re
from datetime import datetime
from datetime import timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup
from nxd.data_product.context import API

_logger = logging.getLogger("ingestion")
_logger.setLevel(logging.INFO)

_MAX_PAGES = 20
_CATEGORIES = ["apparel", "consumables", "household"]


def _parse_price(text: str) -> float | None:
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
        product_id = href.rstrip("/").split("/")[-1]
        name = link.get_text(strip=True)
        price_div = card.select_one("div.price-wrap div.price")
        price_text = price_div.get_text(strip=True) if price_div else ""
        products.append({"product_id": product_id, "name": name, "product_url": href, "price_text": price_text})

    return products


def _scrape_product_detail(session: requests.Session, product_url: str) -> dict:
    resp = session.get(product_url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    description = ""
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "description" in heading.get_text(strip=True).lower():
            para = heading.find_next("p")
            if para:
                description = para.get_text(strip=True)
            break

    brand = ""
    for row in soup.select("table tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2 and cells[0].get_text(strip=True).lower() == "brand":
            brand = cells[1].get_text(strip=True)
            break

    original_price = None
    for node in soup.find_all(string=re.compile(r"from\s+\$\d")):
        match = re.search(r"from\s+\$(\d+(?:\.\d{2})?)", node)
        if match:
            original_price = float(match.group(1))
        break

    return {"description": description, "brand": brand, "original_price": original_price}


def fetch_catalog(source: API) -> pd.DataFrame:
    """Fetch enriched product catalog from web source and return as DataFrame."""
    base_url = source.url.rstrip("/")
    _logger.info("Starting web catalog ingestion from %s", base_url)

    session = requests.Session()
    session.headers.update({"User-Agent": "NextData-Catalog-Scraper/1.0"})

    scraped_at = datetime.now(tz=timezone.utc)
    seen_ids: set[str] = set()
    stubs: list[dict] = []

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

    _logger.info("Collected %d unique products across %d categories", len(stubs), len(_CATEGORIES))

    rows: list[dict] = []
    for stub in stubs:
        try:
            detail = _scrape_product_detail(session, stub["product_url"])
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Failed to scrape detail for product %s: %s", stub["product_id"], exc)
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
    _logger.info("Ingested %d enriched product records", len(df))
    return df
