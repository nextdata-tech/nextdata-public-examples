# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="crm-data-quality",
        description=(
            "Referential-integrity and data-quality findings over the crm-activity "
            "feed: orphan activities, invalid NPIs, inconsistent casing on account "
            "names/status, missing email opt-in, and inactive accounts that still "
            "have logged activity. The transform runs as SQL on Snowflake compute; "
            "the finding logic itself lives in a Snowpark Python stored procedure "
            "declared and CALLed from transform.sql."
        ),
        domain="COMMERCIAL",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/crm_data_quality",
    )
    .environment("demo")
    .transform(
        sql("transform.sql")
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake")
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
        .promise(data_quality_findings)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config("CRM_DATA_QUALITY").target_table("DATA_QUALITY_FINDINGS", data_quality_findings)
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
