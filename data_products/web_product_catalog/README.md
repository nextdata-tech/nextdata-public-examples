# web-product-catalog

A data product that scrapes a competitor retail storefront and loads enriched product catalog data into Snowflake for market intelligence and competitive pricing analysis.

## What it does

1. Fetches paginated HTML product listings from [web-scraping.dev/products](https://web-scraping.dev/products) across three merchandising categories — **Apparel**, **Consumables**, and **Household**.
2. Visits each product detail page to enrich listings with full description, brand, and pre-discount price.
3. Writes all records into the `RETAIL_CATALOG.CATALOG_PRODUCTS` Snowflake table on every run.

## Source

| Property | Value |
|----------|-------|
| Site | https://web-scraping.dev/products |
| Pagination | Server-side, one URL per page (`?page=N`) |
| Categories | `apparel`, `consumables`, `household` |
| Total products | ~28 across 6 pages |

## Output model — `catalog_products`

| Field | Type | Description |
|-------|------|-------------|
| `product_id` | `VARCHAR` | Unique product identifier from the URL path |
| `name` | `VARCHAR` | Product display name |
| `category` | `VARCHAR` | Merchandising category |
| `price` | `NUMBER(8,2)` | Current listed price in USD |
| `original_price` | `NUMBER(8,2)` | Pre-discount price, when a markdown is active |
| `description` | `VARCHAR` | Full product description text |
| `brand` | `VARCHAR` | Brand name from the product features table |
| `product_url` | `VARCHAR` | Canonical URL of the product detail page |
| `scraped_at` | `TIMESTAMP_NTZ` | UTC timestamp of when the record was captured |

## Local run (no Snowflake required)

```bash
# from tests/ directory, with dependencies installed:
cd tests/
python test.py                                  # scrapes https://web-scraping.dev
python test.py https://web-scraping.dev         # explicit URL
python test.py https://web-scraping.dev out.csv # save results to CSV
```

## Deploy

```bash
nxd launch --debug-mode
```
