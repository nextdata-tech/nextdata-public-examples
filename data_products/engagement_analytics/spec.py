# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="engagement-analytics",
        description=(
            "Downstream commercial analytics over the crm-activity field-sales "
            "feed. Reads the upstream CRM activity table in Snowflake and fans "
            "out to two analytical models: channel effectiveness and "
            "cost-efficiency, and monthly engagement trends."
        ),
        domain="COMMERCIAL/ANALYTICS",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/engagement_analytics",
    )
    .environment("demo")
    .transform(
        sql("transform.sql").compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake")
    )
    .input(
        "crm_activity",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/crm-activity#/output/port/snowflake")
        .expectation(activity),
    )
    .output(
        data_product_output()
        .promise(channel_effectiveness)
        .promise(monthly_trends)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config(schema="ENGAGEMENT_ANALYTICS")
                .target_table("CHANNEL_EFFECTIVENESS", channel_effectiveness)
                .target_table("MONTHLY_TRENDS", monthly_trends)
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
