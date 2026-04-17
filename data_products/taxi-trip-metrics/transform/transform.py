import logging

from nxd import data_product
from nxd.core.context import DatabricksWrite
from pyspark.sql import SparkSession
from pyspark.sql.types import DoubleType
from pyspark.sql.types import IntegerType
from pyspark.sql.types import StringType
from pyspark.sql.types import StructField
from pyspark.sql.types import StructType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@data_product.on_transform()
def do_it(spark: SparkSession, databricks: DatabricksWrite):
    """Transform function that populates trip metrics table with sample taxi data."""
    logger.info("Starting taxi trip metrics transform")

    trip_metrics_table = databricks.full_table_name("trip_metrics")
    pipeline_summary_table = databricks.full_table_name("pipeline_summary")

    trip_metrics_schema = StructType(
        [
            StructField("pickup_zip", StringType(), False),
            StructField("trip_count", IntegerType(), False),
            StructField("avg_fare", DoubleType(), False),
        ]
    )

    pipeline_summary_schema = StructType(
        [
            StructField("pipeline", StringType(), False),
            StructField("status", StringType(), False),
            StructField("rows_processed", IntegerType(), False),
        ]
    )

    trip_metrics_df = spark.createDataFrame(
        [
            ("43016", 25, 22.0),
            ("90210", 34, 12.0),
            ("60208", 66, 91.32),
            ("85342", 15, 7.55),
        ],
        schema=trip_metrics_schema,
    )

    pipeline_summary_df = spark.createDataFrame(
        [
            ("taxi_ingestion", "success", 1400),
            ("trip_metrics_aggregation", "success", 950),
            ("fare_quality_check", "failed", 120),
        ],
        schema=pipeline_summary_schema,
    )

    trip_metrics_df.write.format("delta").mode("overwrite").saveAsTable(trip_metrics_table)
    pipeline_summary_df.write.format("delta").mode("overwrite").saveAsTable(pipeline_summary_table)

    logger.info(f"Updated delta table {trip_metrics_table} with {trip_metrics_df.count()} records")
    logger.info(f"Updated delta table {pipeline_summary_table} with {pipeline_summary_df.count()} records")


if __name__ == "__main__":
    data_product.main()
