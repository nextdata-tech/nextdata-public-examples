# ruff: noqa: F403, F405
from nxd_models import *

catalog_products = (
    semantic_model(
        name="catalog_products",
        description="Retail product listings scraped from a competitor web storefront, enriched with "
        "pricing, category classification, and brand attributes for market intelligence "
        "and competitive pricing analysis.",
    )
    .sampling(SamplingMethod.Random)
    .schema(
        {
            "product_id": (string(), "Unique product identifier extracted from the catalog URL path."),
            "name": (string(), "Product display name as listed in the catalog."),
            "category": (string(), "Merchandising category of the product (e.g., Apparel, Consumables, Household)."),
            "price": (decimal(8, 2), "Current listed price in USD as shown on the catalog detail page."),
            "original_price": (
                decimal(8, 2),
                "Pre-discount listed price in USD, populated when a markdown or promotion is active.",
            ),
            "description": (string(), "Full product description text extracted from the catalog detail page."),
            "brand": (string(), "Brand name of the product as listed in the product features table."),
            "product_url": (string(), "Canonical URL of the product detail page on the source storefront."),
            "scraped_at": (
                timestamp(unit=DurationUnit.Nanoseconds),
                "UTC timestamp when this product record was captured from the catalog.",
            ),
        }
    )
)
