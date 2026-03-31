import logging
import sys

from nxd.core.context import DatabricksWrite
from nxd.core.context import Snowflake
from pyspark.sql import DataFrame
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType
from pyspark.sql.types import LongType
from pyspark.sql.types import StringType
from pyspark.sql.types import StructField
from pyspark.sql.types import StructType
from snowflake.connector import connect

TABLES = ["TERM_DEPOSITS", "HOME_LOAN_RATES"]

TARGET_SCHEMAS = {
    "term_deposits": StructType(
        [
            StructField("name", StringType(), True),
            StructField("bank", StringType(), True),
            StructField("min_amount", LongType(), True),
            StructField("max_amount", LongType(), True),
            StructField("min_term", LongType(), True),
            StructField("max_term", LongType(), True),
            StructField("monthly_rate", DecimalType(4, 2), True),
            StructField("annual_rate", DecimalType(4, 2), True),
            StructField("maturity_rate", DecimalType(4, 2), True),
        ]
    ),
    "home_loan_rates": StructType(
        [
            StructField("bank", StringType(), True),
            StructField("product", StringType(), True),
            StructField("loan_term", LongType(), True),
            StructField("min_lvr", LongType(), True),
            StructField("max_lvr", LongType(), True),
            StructField("min_loan", LongType(), True),
            StructField("max_loan", LongType(), True),
            StructField("rate", DecimalType(6, 2), True),
        ]
    ),
}


_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)

if not _logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    )
    _logger.addHandler(handler)

_logger.propagate = False


def _cast_to_target_schema(df: DataFrame, target_schema: StructType) -> DataFrame:
    return df.select(
        [
            F.col(field.name).cast(field.dataType).alias(field.name)
            for field in target_schema.fields
        ]
    )


def _raw_string_schema(target_schema: StructType) -> StructType:
    return StructType(
        [StructField(field.name, StringType(), True) for field in target_schema.fields]
    )


def transform(
    spark: SparkSession,
    product_competitiveness: Snowflake,
    nxd_databricks_storage: DatabricksWrite,
) -> None:
    _logger.info("Starting transform function")
    snowflake_conn = connect(
        user=product_competitiveness.user,
        password=product_competitiveness.password,
        role=product_competitiveness.role,
        account=product_competitiveness.account,
        warehouse=product_competitiveness.warehouse,
        database=product_competitiveness.database,
        schema=product_competitiveness.schema,
    )
    _logger.info("Successfully connected to Snowflake")
    snowflake_cursor = snowflake_conn.cursor()

    try:
        for table_name in TABLES:
            model_name = table_name.lower()
            target_table = nxd_databricks_storage.full_table_name(model_name)
            target_schema = TARGET_SCHEMAS[model_name]

            _logger.info(f"Processing table: {table_name}")
            _logger.info(
                f"Querying Snowflake for records from bank 'Westpac' in table "
                f"{product_competitiveness.schema}.{table_name}"
            )

            select_columns = ", ".join(field.name for field in target_schema.fields)

            snowflake_cursor.execute(
                f"SELECT {select_columns} FROM {product_competitiveness.schema}.{table_name} "
                "WHERE bank = 'Westpac'"
            )
            rows = snowflake_cursor.fetchall()

            _logger.info(
                f"Fetched {len(rows)} records from Snowflake for table {table_name}"
            )

            if not rows:
                _logger.info(
                    f"No rows returned for {table_name}; skipping Spark write to {target_table}"
                )
                continue

            rows_as_strings = [
                tuple(None if value is None else str(value) for value in row)
                for row in rows
            ]
            raw_df = spark.createDataFrame(
                rows_as_strings,
                schema=_raw_string_schema(target_schema),
            )
            spark_df = _cast_to_target_schema(raw_df, target_schema)

            spark_df.write.format("delta").mode("overwrite").saveAsTable(target_table)
            _logger.info(f"Written {len(rows)} rows to Databricks table {target_table}")
    finally:
        snowflake_cursor.close()
        snowflake_conn.close()
