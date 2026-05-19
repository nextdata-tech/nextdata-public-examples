# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="open-meteo-loader",
        description="Ingests current weather conditions from the Open-Meteo public API "
        "and writes normalized records into Snowflake using the canonical weather schema.",
        domain="WEATHER/INGESTION",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/open_meteo_loader",
    )
    .environment("demo")
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
        .when(scheduled("0 * * * *"), startup=True)
    )
    .input(
        "open-meteo-api",
        source_aligned_input().source(
            "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/open-meteo-api"
        ),
    )
    .output(
        data_product_output()
        .model(open_meteo_model)
        .promise(open_meteo_model)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config("WEATHER").target_table("OPEN_METEO", open_meteo_model)
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
