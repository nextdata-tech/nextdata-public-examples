import logging
from datetime import datetime
from datetime import timezone
from urllib.parse import quote

import requests
from nxd.core.context import Snowflake
from nxd.data_product.context import API
from snowflake.connector import connect

_logger = logging.getLogger("wttr_loader.transform")

CITIES = ["Barcelona", "New York", "Tokyo", "London"]


def _fetch(city: str, base_url: str) -> dict:
    resp = requests.get(
        f"{base_url}/{quote(city)}",
        params={"format": "j1"},
        timeout=20,
    )
    resp.raise_for_status()
    current = resp.json()["current_condition"][0]
    return {
        "city": city,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_c": float(current["temp_C"]),
        "humidity_pct": int(current["humidity"]),
        "wind_speed_kmh": float(current["windspeedKmph"]),
    }


def transform(wttr_in_api: API, snowflake: Snowflake) -> None:
    base_url = wttr_in_api.url.rstrip("/")
    rows = [_fetch(city, base_url) for city in CITIES]
    _logger.info("Fetched %d records from wttr.in", len(rows))

    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE WTTR")
    cursor.executemany(
        "INSERT INTO WTTR (city, timestamp, temperature_c, humidity_pct, wind_speed_kmh) "
        "VALUES (%s, %s::TIMESTAMP_NTZ, %s, %s, %s)",
        [(r["city"], r["timestamp"], r["temperature_c"], r["humidity_pct"], r["wind_speed_kmh"]) for r in rows],
    )
    conn.commit()
    conn.close()
    _logger.info("Loaded %d records into WTTR", len(rows))
