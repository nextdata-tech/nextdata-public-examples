# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="drug-safety-signals",
        domain="pharmacovigilance/safety",
        description=(
            "Pharmacovigilance domain — Drug Safety team. "
            "FAERS-shaped adverse-event summary per product, region, and reporting period: "
            "total and serious adverse events, hospitalisations, deaths, leading MedDRA "
            "System Organ Class, and primary-suspect case count. "
            "Provides the numerator for the reporting-rate metric. "
            "All data is SYNTHETIC; products are FICTIONAL. "
            "Join key: product_id + region + report_period."
        ),
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
    )
    .environment("demo")
    .transform(
        sql("transform/load_safety_data.sql")
        .compute("https://nextopia.dev/infra-profile/ecommerce-demo#/services/nxd-snowflake")
        .when(scheduled("0 0 * * *"), startup=True)
    )
    .output(
        data_product_output()
        .model(adverse_event_summary)
        .port(
            "snowflake",
            storage("https://nextopia.dev/infra-profile/ecommerce-demo#/services/nxd-snowflake")
            .config(
                snowflake_config(schema="drug_safety_signals")
                .target_table("adverse_event_summary", adverse_event_summary)
            )
            .model(adverse_event_summary)
            .promise(adverse_event_summary),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
