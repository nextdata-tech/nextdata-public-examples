# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="credit-card-tx",
        description="Linking customers with their credit card transactions, capturing key details such as transaction amounts, types, merchants, and locations to support analysis, monitoring, and reporting.",
        domain="RISK/FRAUD",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-examples",
    )
    .environment("demo")
    .with_global_trigger(ScheduleTrigger("0 */8 * * *"))
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
    )
    .output(
        data_product_output()
        .promise(transactions)
        .promise(customers)
        # policy "credit-card-tx-pii-compliance" enforces that this promise must be present
        .promise(
            custom("credit-card-tx-pii-compliance")
            .script("contracts/pii_compliance.py")
            .service(service_name="adls", driver="nxd:adls:1.0.0")
            .description("PII Compliance Contract for credit-card-tx - Customers")
            .model(customers)
        )
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
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
