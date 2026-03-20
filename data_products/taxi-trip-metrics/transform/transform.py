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

    schema = StructType(
        [
            StructField("pickup_zip", StringType(), False),
            StructField("trip_count", IntegerType(), False),
            StructField("avg_fare", DoubleType(), False),
        ]
    )

    df = spark.createDataFrame(
        [
            ("43016", 25, 22.0),
            ("90210", 34, 12.0),
            ("60208", 66, 91.32),
            ("85342", 15, 7.55),
        ],
        schema=schema,
    )

    df.write.format("delta").mode("overwrite").saveAsTable(trip_metrics_table)
    logger.info(f"Updated delta table {trip_metrics_table} with {df.count()} records")


if __name__ == "__main__":
    data_product.main()
