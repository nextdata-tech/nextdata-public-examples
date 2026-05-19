import logging
from datetime import datetime
from datetime import timezone

import requests
from nxd.core.context import Snowflake
from nxd.data_product.context import API
from snowflake.connector import connect

_logger = logging.getLogger("open_meteo_loader.transform")

CITIES = [
    {"name": "Barcelona", "lat": 41.3874, "lon": 2.1686},
    {"name": "New York", "lat": 40.7128, "lon": -74.0060},
    {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503},
    {"name": "London", "lat": 51.5074, "lon": -0.1278},
]


def _normalize_timestamp(raw: str) -> str:
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _fetch(city: dict, base_url: str) -> dict:
    resp = requests.get(
        f"{base_url}/v1/forecast",
        params={
            "latitude": city["lat"],
            "longitude": city["lon"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "timezone": "UTC",
        },
        timeout=20,
    )
    resp.raise_for_status()
    current = resp.json()["current"]
    return {
        "city": city["name"],
        "timestamp": _normalize_timestamp(current["time"]),
        "temperature_c": float(current["temperature_2m"]),
        "humidity_pct": int(current["relative_humidity_2m"]),
        "wind_speed_kmh": float(current["wind_speed_10m"]),
    }


def transform(open_meteo_api: API, snowflake: Snowflake) -> None:
    base_url = open_meteo_api.url.rstrip("/")
    rows = [_fetch(city, base_url) for city in CITIES]
    _logger.info("Fetched %d records from Open-Meteo", len(rows))

    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE OPEN_METEO")
    cursor.executemany(
        "INSERT INTO OPEN_METEO (city, timestamp, temperature_c, humidity_pct, wind_speed_kmh) "
        "VALUES (%s, %s::TIMESTAMP_NTZ, %s, %s, %s)",
        [(r["city"], r["timestamp"], r["temperature_c"], r["humidity_pct"], r["wind_speed_kmh"]) for r in rows],
    )
    conn.commit()
    conn.close()
    _logger.info("Loaded %d records into OPEN_METEO", len(rows))
