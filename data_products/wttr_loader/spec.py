# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="wttr-loader",
        description="Ingests current weather conditions from the wttr.in public API "
        "and writes normalized records into Snowflake using the canonical weather schema.",
        domain="WEATHER/INGESTION",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/wttr_loader",
    )
    .environment("demo")
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
        .when(scheduled("0 */8 * * *"), startup=True)
    )
    .input(
        "wttr-in-api",
        source_aligned_input().source("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/wttr-in-api"),
    )
    .output(
        data_product_output()
        .model(wttr_model)
        .promise(wttr_model)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config("WEATHER").target_table("WTTR", wttr_model)
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
