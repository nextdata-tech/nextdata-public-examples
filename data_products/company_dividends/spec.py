# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="company-dividends",
        domain="FINANCE/COMPETITORS/FINANCIAL-PERFORMANCE",
        description="Dividend information obtained through competitor website analysis",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/company_dividends",
    )
    .environment("demo")
    .with_global_trigger(ScheduleTrigger("10,30,50 * * * *"))
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
    )
    .output(
        data_product_output()
        .promise(dividends)
        .port(
            "adls",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/adls")
            .config(adls_config(file_type=SupportedFormat.JSON))
            .managed_access()
            .promise(
                custom("adls-non-empty-output")
                .verify(code(adls_freshness.verify))
                .description("Verifies each promised output model in ADLS contains at least one record")
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
