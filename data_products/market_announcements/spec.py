# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="market-announcements",
        description="Company announcements released to the National Association of Securities Dealers Automated Quotations (NASDAQ), including metadata, associated companies, and document details.",
        domain="regulatory-compliance",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-examples",
    )
    .environment("demo")
    .with_global_trigger(ScheduleTrigger("0 12 * * *"))
    .transform(
        script("transform.py").compute(
            "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute"
        )
    )
    .output(
        data_product_output()
        .model(companies)
        .model(announcements)
        .promise(companies)
        .promise(announcements)
        .port(
            "adls",
            storage(
                "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/adls"
            )
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
