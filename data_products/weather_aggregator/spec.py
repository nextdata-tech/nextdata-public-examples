# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="weather-aggregator",
        description="Reads normalized weather records from all provider loaders via Snowflake, "
        "unions them into a single unified dataset using Snowpark, and appends a provider field "
        "to identify the source of each record.",
        domain="WEATHER/AGGREGATION",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/weather_aggregator",
    )
    .environment("demo")
    .input(
        "open-meteo-data",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/open-meteo-loader#/output/port/snowflake")
        .model(open_meteo_model)
        .expectation(open_meteo_model)
        .environment("demo"),
    )
    .input(
        "wttr-data",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/wttr-loader#/output/port/snowflake")
        .model(wttr_model)
        .expectation(wttr_model)
        .environment("demo"),
    )
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
        .when(any_of(updated("open-meteo-data"), updated("wttr-data")))
    )
    .output(
        data_product_output()
        .model(unified_weather_model)
        .promise(unified_weather_model)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config("WEATHER").target_table("UNIFIED", unified_weather_model)
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
