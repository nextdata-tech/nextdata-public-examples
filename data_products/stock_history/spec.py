# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="stock-history",
        description="Historical price and trading volume data for NASDAQ listed stocks from competitor analysis",
        domain="FINANCE/COMPETITORS/FINANCIAL-PERFORMANCE",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-examples",
    )
    .environment("demo")
    .with_global_trigger(ScheduleTrigger("0 */8 * * *"))
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks")
        .config(cluster_config)
    )
    .output(
        data_product_output()
        .promise(history)
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
