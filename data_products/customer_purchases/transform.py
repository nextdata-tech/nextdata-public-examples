"""Databricks streaming example with input/output model verification."""

import logging

from nxd import data_product
from nxd.core.context import Databricks
from nxd.core.context import DatabricksWrite
from nxd.core.context import S3Input
from nxd.core.context import VerifyResult
from nxd.core.context import VerifyResultEnum

_logger = logging.getLogger("transform.streaming")
_logger.setLevel(logging.INFO)


# =============================================================================
# Per-Batch Streaming Verification (Custom Promises)
# =============================================================================
# Uses foreach_batch mode: the SDK intercepts toTable() → foreachBatch + start(),
# giving each verification function the full micro-batch DataFrame.


@data_product.on_verify(per_batch=True, name="streaming_batch_quality")
def check_batch_quality(df, batch_id: int) -> VerifyResult:
    """Check basic quality metrics for each streaming micro-batch.

    Verifies row count and checks for null values in critical fields.
    Runs automatically on every micro-batch via foreachBatch interception.
    """
    _logger.info(f"Validating batch {batch_id}...")
    row_count = df.count()

    if row_count == 0:
        return VerifyResult(
            result=VerifyResultEnum.PASS,
            context={"batch_id": batch_id, "row_count": 0, "status": "empty_batch"},
        )

    # Check for null values in critical fields
    from pyspark.sql.functions import col
    from pyspark.sql.functions import count
    from pyspark.sql.functions import when

    null_counts = df.select(
        count(when(col("timestamp").isNull(), 1)).alias("null_timestamps"),
        count(when(col("value").isNull(), 1)).alias("null_values"),
        count(when(col("message").isNull(), 1)).alias("null_messages"),
    ).first()

    null_total = null_counts["null_timestamps"] + null_counts["null_values"] + null_counts["null_messages"]

    if null_total > 0:
        _logger.warning(f"Batch {batch_id}: found {null_total} null values across {row_count} rows")
        return VerifyResult(
            result=VerifyResultEnum.WARNING,
            context={
                "batch_id": batch_id,
                "row_count": row_count,
                "null_timestamps": null_counts["null_timestamps"],
                "null_values": null_counts["null_values"],
                "null_messages": null_counts["null_messages"],
            },
        )

    _logger.info(f"Batch {batch_id}: {row_count} rows, all quality checks passed")
    return VerifyResult(
        result=VerifyResultEnum.PASS,
        context={"batch_id": batch_id, "row_count": row_count},
    )


def _run_spark_streaming(databricks: Databricks | DatabricksWrite, s3_input: S3Input) -> None:
    """Run Spark Structured Streaming with NXD model verification."""
    from nxd.drivers.databricks import NxdDatabricksSession
    from pyspark.sql.functions import concat
    from pyspark.sql.functions import lit

    _logger.info("Creating NxdDatabricksSession...")
    nxd_spark = NxdDatabricksSession.connect(databricks)

    input_model = s3_input.models.get("rate_model")

    _logger.info("Setting up rate stream source...")
    read_stream = nxd_spark.readStream

    if input_model:
        _logger.info("Input model verification: enabled (rate_model)")
        read_stream = read_stream.model(input_model)
    else:
        _logger.warning("Input model 'rate_model' not found in S3 context")

    input_stream_df = read_stream.format("rate").option("rowsPerSecond", 1).load()
    _logger.info(f"Input stream schema: {input_stream_df.schema}")

    from pyspark.sql import SparkSession

    active_session = SparkSession.getActiveSession()
    _logger.info(f"SparkSession.getActiveSession(): {active_session is not None}")

    transformed_df = input_stream_df.withColumn("message", concat(lit("Seen: "), input_stream_df.value.cast("string")))

    from pyspark.sql import functions as F
    from pyspark.sql.types import IntegerType
    from pyspark.sql.types import TimestampNTZType

    transformed_df = transformed_df.withColumn("timestamp", F.col("timestamp").cast(TimestampNTZType()))
    transformed_df = transformed_df.withColumn("value", F.col("value").cast(IntegerType()))

    _logger.info(f"Transformed stream schema (table-aligned): {transformed_df.schema}")

    table_name = databricks.model_tables.get("output_model", "streaming_output")
    output_table = databricks.full_table_name("output_model")
    output_model = databricks.models.get("output_model")

    checkpoint_path = f"/Volumes/{databricks.catalog}/{databricks.schema}/checkpoints/{table_name}"

    _logger.info(f"Output table: {output_table}")
    _logger.info(f"Checkpoint path: {checkpoint_path}")
    _logger.info(f"Model verification: {'enabled' if output_model else 'disabled'}")

    write_stream = transformed_df.writeStream

    if output_model:
        _logger.info("Verifying output against model: output_model")
        write_stream = write_stream.model(output_model)

    write_stream = (
        write_stream.format("delta")
        .option("mergeSchema", "true")
        .option("checkpointLocation", checkpoint_path)
        .trigger(processingTime="15 seconds")
    )

    _logger.info("Starting Spark Structured Streaming query...")
    _logger.info("Per-batch validation (check_batch_quality) will run for each micro-batch")
    query = write_stream.toTable(output_table)

    _logger.info(f"Streaming query {query.id} started")
    _logger.info("ProgressReporter will send PROGRESS events to kernel on each batch")
    _logger.info("PromiseVerification events will be sent after each batch validation")
    query.awaitTermination()


@data_product.on_transform()
def transform(output: DatabricksWrite, s3_source: S3Input) -> None:
    """Continuous streaming transform with model verification."""
    _logger.info(f"Context type: {type(output).__name__}")
    _logger.info(f"Databricks cluster_id: {output.cluster_id}")
    _logger.info(f"Databricks workspace_url: {getattr(output, 'workspace_url', None)}")
    _logger.info(f"Auth method: {'Service Principal' if getattr(output, 'tenant_id', None) else 'PAT'}")
    _logger.info(
        f"Has credentials: {bool(getattr(output, 'tenant_id', None) or getattr(output, 'private_access_token', None))}"
    )
    _logger.info(f"S3 source models: {list(s3_source.models.keys())}")

    _run_spark_streaming(output, s3_source)


if __name__ == "__main__":
    data_product.main()
