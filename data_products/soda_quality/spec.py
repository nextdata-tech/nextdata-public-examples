# ruff: noqa: F403, F405
from nxd_spec import *

INFRA_PROFILE_NAME = "ecommerce-demo"

# Schema of the STREAMING_TRANSACTIONS table written by the streaming-transactions DP.
# timestamp: NTZ timestamp (milliseconds), value: monotonically increasing int, message: "Seen: <N>"
input_transactions_model = semantic_model("output_model").schema(
    {
        "timestamp": timestamp(unit=DurationUnit.Milliseconds, timezone=None),
        "value": number(),
        "message": string(),
    }
)

transactions_model = semantic_model("streaming_transactions").schema(
    {
        "timestamp": timestamp(unit=DurationUnit.Milliseconds, timezone=None),
        "value": number(),
        "message": string(),
    }
)


spec = (
    data_product(
        name="soda-quality",
        domain="Streaming",
        version="0.1.0-dev",
        infra_profile=INFRA_PROFILE_NAME,
        description=(
            "Periodic Soda data quality checks on the STREAMING_TRANSACTIONS Databricks table. "
            "Runs every 5 minutes and copies verified rows to SODA_VERIFIED_TRANSACTIONS."
        ),
    )
    .environment("demo")
    .input(
        "databricks-source",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/streaming-transactions#/output/port/output")
        .environment("demo")
        # Declare the model contract first so InputSpec.models is always populated
        .expectation(input_transactions_model)
        .expectation(
            quality(soda, "./contracts/streaming_checks.yml")
            .name("StreamingTransactionsQuality")
            .description(
                "Soda checks on STREAMING_TRANSACTIONS: table is non-empty, "
                "no null values in critical columns, value is non-negative."
            )
        ),
    )
    .output(
        data_product_output()
        .model(transactions_model)
        .promise(transactions_model)
        .port(
            "output",
            storage(f"https://example.com/infra-profile/{INFRA_PROFILE_NAME}#/services/nxd-databricks-sp").config(
                databricks_config().target_table("soda_verified_transactions", transactions_model)
            ),
        ),
    )
    .transform(script("transform/main.py").when(scheduled("0 */4 * * *"), startup=True))
)
