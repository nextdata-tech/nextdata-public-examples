# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="customer-purchases",
        domain="Commerce",
        description="Real-time customer purchase transactions ingested from S3 streaming events and stored in Databricks, enabling analysis of purchasing behaviour and transaction patterns.",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/customer_purchases",
    )
    .environment("demo")
    .input(
        "s3-source",
        source_aligned_input()
        .source("https://example.com/infra-profile/ecommerce-demo#/services/s3-output")
        .expectation(rate_model)
        .expectation(
            custom("s3-atleast-one-record")
            .verify(code(s3_atleast_one_record.verify))
            .description("Verifies the S3 streaming input source is configured and accessible")
        )
        .config(s3_config(SupportedFormat.PARQUET).target_file("streaming/input/rate_data.parquet", rate_model)),
    )
    .output(
        data_product_output()
        .model(output_model)
        .promise(output_model)
        .port(
            "output",
            storage("https://example.com/infra-profile/ecommerce-demo#/services/nxd-databricks-sp")
            .config(databricks_config().target_table("STREAMING_TRANSACTIONS", output_model).disable_promotion())
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
        .compute("https://example.com/infra-profile/ecommerce-demo#/services/nxd-databricks-streaming")
        .config(
            {
                "num_workers": 1,
                "spark_version": "15.4.x-scala2.12",
                "store_path": "/Workspace/nxd",
                "startup_timeout_secs": 900,
            }
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
