import logging
import os
import tempfile
import time
import urllib.parse
from datetime import datetime
from datetime import timezone

import duckdb
import pyarrow as pa
import requests
from adlfs.spec import AzureBlobFileSystem
from api import anz
from api import macquarie
from api import westpac
from nxd.core.context import AzureDataLakeStorage

UTC = timezone.utc
_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)


def get_fx_data_url() -> str:
    start_date = int(datetime(1983, 7, 14).timestamp()) * 1000
    end_date = int(datetime.now(UTC).timestamp()) * 1000
    base_url = f"https://api.ofx.com/PublicSite.ApiService/SpotRateHistory/AUD/NZD/-{start_date}/{end_date}"
    params = urllib.parse.urlencode({"DecimalPlaces": "6", "ReportingInterval": "daily", "format": "json"})

    return f"{base_url}?{params}"


def conform_macquarie_data(conn: duckdb.DuckDBPyConnection, data: list[dict]):
    data = pa.Table.from_pylist(data)
    conn.execute(
        r"""
        create table macquarie as
            select
                'Macquarie' as bank,
                date(strptime(payment_date, '%d/%m/%Y')) as payment_date,
                round(cast(divident_per_share as int) / 100, 2) as dividend_per_share
            from data
        """,
    )


def conform_anz_data(conn: duckdb.DuckDBPyConnection, data: list[dict]):
    data = pa.Table.from_pylist(data)
    conn.execute(
        r"""
        create table anz as
            select
                'ANZ' as bank,
                date(strptime(regexp_extract(pay_date, '\d{1,2}/\d{2}/\d{4}'), '%d/%m/%Y')) as payment_date,
                round(cast(regexp_extract(dividend, '[0-9]+') as int) / 100, 2) as dividend_per_share
            from data
        """,
    )


def fetch_with_retries(url, retries=3, delay=2) -> str:
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt == retries:
                raise
            time.sleep(delay * attempt)  # exponential backoff
    return ""


def conform_westpac_data(conn: duckdb.DuckDBPyConnection, data: list[dict]):
    data = pa.Table.from_pylist(data)
    fx_data = fetch_with_retries(get_fx_data_url())
    tmp_path = ""
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json") as tmp:
        tmp.write(fx_data)
        tmp_path = tmp.name

    try:
        conn.execute(
            r"""
            create table westpac as
                with dividend_history as (
                    select
                        date(strptime(regexp_extract(payment_date, '\d{2}/\d{2}/\d{4}'), '%d/%m/%Y')) as payment_date,
                        cast(nullif(regexp_extract(rate, '[0-9.]+'), '') as decimal(6, 2)) / 100 as rate,
                        cast(nullif(regexp_extract(franking_level, '[0-9.]+'), '') as int) / 100 as franking_percentage,
                        cast(nullif(regexp_extract(nz_imputation_credits, '[0-9.]+'), '') as decimal(6, 2)) nz_imputation_credits,
                        cast(nullif(regexp_extract(share_price, '[0-9.]+'), '') as decimal(6, 2)) as share_price,
                        cast(nullif(regexp_extract(divident_bonus_plan, '[0-9.]+'), '') as decimal(6, 2)) as divident_bonus
                    from data
                    where payment_date != '1H20'
                ),

                exchange_rates as (
                    select
                        unnest(historicalPoints, recursive := true)
                    from read_json($fx_data_path)

                ),

                fx as (
                    select
                        PointInTime,
                        date(to_timestamp(PointInTime / 1000)) as date,
                        InterbankRate as interbank_rate,
                        InverseInterbankRate as inverse_interbank_rate
                    from exchange_rates
                )

                select
                    'Westpac' as bank,
                    payment_date,
                    round(dividend_history.rate * fx.interbank_rate, 2) as dividend_per_share,
                from dividend_history
                left join fx
                    on dividend_history.payment_date = fx.date
            """,
            {
                "fx_data_path": tmp_path,
            },
        )
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def transform(
    adls: AzureDataLakeStorage,
) -> None:
    _logger.info("Starting transform")

    filesystem = AzureBlobFileSystem(
        account_name=adls.account_name,
        tenant_id=adls.tenant_id,
        client_id=adls.client_id,
        client_secret=adls.client_secret,
    )
    conn = duckdb.connect()
    conn.register_filesystem(filesystem)

    # ANZ
    anz_dividends = anz.get_dividends()
    conform_anz_data(conn, anz_dividends)

    # Westpac
    westpac_dividends = westpac.get_dividends()
    conform_westpac_data(conn, westpac_dividends)

    # Macquarie
    macquarie_dividends = macquarie.get_dividends()
    conform_macquarie_data(conn, macquarie_dividends)

    conn.execute(
        r"""
        create table output as
            select * from anz
            union all
            select * from westpac
            union all
            select * from macquarie
        """
    )

    output_path = adls.model_paths["dividends"].path
    conn.execute(f"copy output to 'abfs://{adls.container}/{output_path}'")

    _logger.info("Transform completed successfully")
