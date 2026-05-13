import logging

import pandas as pd
from nxd.core.context import Snowflake
from snowflake.connector import connect

_logger = logging.getLogger("loader")


def load_to_snowflake(df: pd.DataFrame, snowflake: Snowflake, table: str = "CATALOG_PRODUCTS") -> None:
    """Truncate and reload Snowflake target table from DataFrame."""
    _logger.info("Loading %d records into Snowflake table %s", len(df), table)

    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()
    cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.executemany(
        f"""
        INSERT INTO {table}
            (product_id, name, category, price, original_price, description, brand, product_url, scraped_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::TIMESTAMP_NTZ)
        """,
        [
            (
                row["product_id"],
                row["name"],
                row["category"],
                row["price"],
                row["original_price"],
                row["description"],
                row["brand"],
                row["product_url"],
                row["scraped_at"].isoformat() if pd.notna(row["scraped_at"]) else None,
            )
            for _, row in df.iterrows()
        ],
    )
    conn.commit()
    conn.close()
    _logger.info("Successfully loaded %d records into %s", len(df), table)
