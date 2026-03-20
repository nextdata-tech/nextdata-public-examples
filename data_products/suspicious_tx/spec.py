# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="suspicious-tx",
        description="Suspicious credit card transactions that occur in different countries within the same hour for the same customer, supporting fraud detection and anomaly analysis.",
        domain="RISK/FRAUD",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-examples",
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
        .expectation(transactions),
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
            .managed_access(),
        )
    )
    .control("owner", owner().user("hello@nextdata.com"))
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
)
