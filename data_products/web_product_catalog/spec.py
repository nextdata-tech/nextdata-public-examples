# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="web-product-catalog",
        description="Retail product catalog data scraped from a competitor web storefront, "
        "enriched with pricing, category, and brand attributes for market intelligence "
        "and competitive pricing analysis.",
        domain="RETAIL/CATALOG/PRICING",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/web_product_catalog",
    )
    .environment("demo")
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
        .when(scheduled("0 */8 * * *"), startup=True)
    )
    .input(
        "catalog-source",
        source_aligned_input()
        .source("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/web-catalog-api")
        .model(catalog_products)
        .expectation(catalog_products),
    )
    .output(
        data_product_output()
        .promise(catalog_products)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config("RETAIL_CATALOG").target_table("CATALOG_PRODUCTS", catalog_products)
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
