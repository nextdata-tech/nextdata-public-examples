# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="commercial-prescriptions",
        domain="commercial/analytics",
        description=(
            "Commercial Analytics domain. "
            "Prescription volume per product, region, and reporting period: "
            "total (TRx) and new (NRx) prescriptions, distinct patients, units dispensed, "
            "average days of therapy, and prescriber count. "
            "Provides the denominator for the federated reporting-rate metric. "
            "All data is SYNTHETIC; products are FICTIONAL. "
            "Join key: product_id + region + report_period."
        ),
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
    )
    .environment("demo")
    .transform(
        sql("transform/load_commercial_data.sql")
        .compute("https://nextopia.dev/infra-profile/ecommerce-demo#/services/nxd-snowflake")
        .when(scheduled("0 0 * * *"), startup=True)
    )
    .output(
        data_product_output()
        .model(prescription_volume)
        .port(
            "snowflake",
            storage("https://nextopia.dev/infra-profile/ecommerce-demo#/services/nxd-snowflake")
            .config(
                snowflake_config(schema="commercial_prescriptions")
                .target_table("prescription_volume", prescription_volume)
            )
            .model(prescription_volume)
            .promise(prescription_volume),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
