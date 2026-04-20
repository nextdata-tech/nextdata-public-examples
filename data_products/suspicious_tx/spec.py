# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="suspicious-tx",
        description="Suspicious credit card transactions that occur in different countries within the same hour for the same customer, supporting fraud detection and anomaly analysis.",
        domain="RISK/FRAUD",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/suspicious_tx",
    )
    .environment("demo")
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
    )
    .input(
        "credit_card_tx",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/credit-card-tx#/output/port/adls")
        .expectation(transactions)
        .expectation(
            custom("adls-non-empty-input")
            .verify(code(adls_input_check.verify))
            .description("Verifies the incoming credit card transaction data contains at least one record")
        ),
    )
    .output(
        data_product_output()
        .promise(anomalies)
        .port(
            "adls",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/adls")
            .config(
                adls_config(
                    file_type=SupportedFormat.PARQUET,
                )
            )
            .managed_access()
            .promise(
                custom("adls-non-empty-output")
                .verify(code(adls_freshness.verify))
                .description("Verifies each promised output model in ADLS was updated within the last 24 hours")
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
