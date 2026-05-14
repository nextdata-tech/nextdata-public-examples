from datetime import datetime
from datetime import timezone

from nxd import data_product
from nxd.data_product.context import Snowflake
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum
from snowflake.connector import connect
from snowflake.connector.connection import SnowflakeConnection

FRESHNESS_THRESHOLD_HOURS = 10


def _connect(snowflake: Snowflake) -> SnowflakeConnection:
    return connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )


@data_product.on_verify()
def verify(snowflake: Snowflake) -> VerifyResult:
    conn = _connect(snowflake)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(scraped_at) FROM CATALOG_PRODUCTS")
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row or row[0] is None:
        return VerifyResult(VerifyResultEnum.FAILED, {"result": "No rows in CATALOG_PRODUCTS"})

    max_scraped_at = row[0]
    if max_scraped_at.tzinfo is None:
        max_scraped_at = max_scraped_at.replace(tzinfo=timezone.utc)

    age_hours = (datetime.now(tz=timezone.utc) - max_scraped_at).total_seconds() / 3600
    if age_hours > FRESHNESS_THRESHOLD_HOURS:
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {"result": f"Data stale: max scraped_at is {age_hours:.1f}h ago (threshold {FRESHNESS_THRESHOLD_HOURS}h)"},
        )
    return VerifyResult(
        VerifyResultEnum.PASS,
        {"result": f"Data fresh: scraped {age_hours:.1f}h ago"},
    )


if __name__ == "__main__":
    data_product.verify()
