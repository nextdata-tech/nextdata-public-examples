import logging

import pyarrow as pa
import yfinance as yf
from models import history as history_model
from nxd.data_product.context import AzureDataLakeStorage
from pyspark.sql import SparkSession
from utils import parquet_to_adls

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)


def _retrieve_history(tickers: yf.Tickers) -> pa.Table:
    history = tickers.history(
        period="5y",
        interval="1d",
        progress=False,
    )
    if history is None:
        raise ValueError(
            f"No history data returned by yfinance for symbols - {tickers.symbols}"
        )

    columns = {
        "Ticker": "symbol",
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "Dividends": "dividends",
        "Stock Splits": "stock_splits",
    }

    history = history.stack(1, future_stack=True).reset_index()
    history = history.rename(columns=columns)
    history = history[columns.values()]
    history = pa.Table.from_pandas(
        history,
        preserve_index=False,
    )

    return history


def transform(
    spark: SparkSession,
    adls: AzureDataLakeStorage,
) -> None:
    _logger.info("Starting stock-history transformation...")

    symbols = [
        "WBC.AX",
        # "CBA.AX",
        "ANZ.AX",
        # "NAB.AX",
        "MQG.AX",
    ]
    tickers = yf.Tickers(symbols)

    history = _retrieve_history(tickers)

    parquet_to_adls(adls, history, adls.model_paths[history_model.name].path)

    _logger.info("Transform completed successfully")
