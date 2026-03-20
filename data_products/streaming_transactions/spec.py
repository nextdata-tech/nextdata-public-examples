# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="streaming-transactions",
        domain="Streaming",
        version="0.1.1-dev",
        infra_profile="ecommerce-demo",
    )
    .environment("demo")
    .input(
        "s3-source",
        source_aligned_input()
        .source("https://example.com/infra-profile/ecommerce-demo#/services/s3-output")
        .expectation(rate_model)
        .config(
            s3_config(SupportedFormat.PARQUET).target_file(
                "streaming/input/rate_data.parquet", rate_model
            )
        ),
    )
    .output(
        data_product_output()
        .model(output_model)
        .promise(output_model)
        .port(
            "output",
            storage(
                "https://example.com/infra-profile/ecommerce-demo#/services/nxd-databricks-sp"
            )
            .config(
                databricks_config()
                .target_table("STREAMING_TRANSACTIONS", output_model)
                .disable_promotion()
            )
            .promise(
                custom("streaming_batch_quality")
                .description("Per-batch data quality checks on streaming output")
                .model(output_model)
                .script("transform.py")
            ),
        )
    )
    .transform(
        script("transform.py")
        .compute(
            "https://example.com/infra-profile/ecommerce-demo#/services/nxd-databricks-streaming"
        )
        .config(
            {
                "num_workers": 1,
                "spark_version": "15.4.x-scala2.12",
                "store_path": "/Workspace/nxd",
                "startup_timeout_secs": 900,
            }
        )
    )
)
