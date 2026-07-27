# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="rep-territory-performance",
        description=(
            "Rep and territory sales-performance analytics over the crm-activity "
            "field-sales feed. Reads the upstream CRM activity table in Snowflake "
            "and produces a rep/territory scorecard, including a field-vs-HQ "
            "campaign flag (MKTG-01 / T-MKT)."
        ),
        domain="COMMERCIAL/SALES-PERFORMANCE",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/rep_territory_performance",
    )
    .environment("demo")
    .provision(sql("provision.sql"))
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
        .promise(rep_territory_scorecard)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config(schema="REP_TERRITORY_PERFORMANCE").target_table(
                    "REP_TERRITORY_SCORECARD", rep_territory_scorecard
                )
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
