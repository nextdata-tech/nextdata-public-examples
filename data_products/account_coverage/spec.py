# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="account-coverage",
        description=(
            "Per-account coverage and value-gap analysis over the crm-activity "
            "feed: realized vs. potential value, touch volume, cost, engagement, "
            "and an opinionated coverage classification flagging under-served "
            "high-value and over-served low-value accounts. The transform runs "
            "as SQL on Snowflake compute; the coverage logic itself lives in a "
            "Snowpark Python stored procedure declared and CALLed from "
            "transform.sql."
        ),
        domain="COMMERCIAL/ANALYTICS",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/account_coverage",
    )
    .environment("demo")
    .transform(
        sql("transform.sql").compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake")
    )
    .input(
        "crm_activity",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/crm-activity#/output/port/snowflake")
        .expectation(account)
        .expectation(activity),
    )
    .output(
        data_product_output()
        .promise(account_coverage)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config("ACCOUNT_COVERAGE").target_table("ACCOUNT_COVERAGE", account_coverage)
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
