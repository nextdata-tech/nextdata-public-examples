import logging

import pandas as pd
import pyarrow as pa
import yfinance as yf
from models import income_statements as income_statements_model
from nxd.data_product.context import AzureDataLakeStorage
from utils import parquet_to_adls

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)

# Define explicit PyArrow schema to match model definition
INCOME_STATEMENTS_SCHEMA = pa.schema(
    [
        pa.field("metric", pa.string()),
        pa.field("date", pa.timestamp("ns")),
        pa.field("value", pa.float64()),
        pa.field("symbol", pa.string()),
    ]
)


def _format_financial_report_dataframe(
    dataframe: pd.DataFrame, symbol: str, acronyms: list[str] | None = None
) -> pd.DataFrame:
    dataframe.index = yf.utils.camel2title(dataframe.index, sep="_", acronyms=acronyms)  # type: ignore
    dataframe.index = dataframe.index.str.lower()  # type: ignore

    dataframe = dataframe.reset_index(names="metric")
    # Convert all column names to strings (yfinance returns datetime column names)
    dataframe.columns = dataframe.columns.astype(str)
    dataframe = dataframe.melt(
        id_vars="metric",
        var_name="date",
        value_name="value",
    )
    dataframe["date"] = pd.to_datetime(dataframe["date"])
    dataframe["symbol"] = symbol

    return dataframe


def _retrieve_income_statements(tickers: yf.Tickers) -> pa.Table:
    income_statements: list[pd.DataFrame] = []
    for symbol, ticker in tickers.tickers.items():
        income = ticker.get_income_stmt(pretty=False, freq="yearly")
        if isinstance(income, dict):
            raise TypeError(f"Income statement returned as dict by yfinance for symbol - {symbol}")

        income = _format_financial_report_dataframe(
            income,
            acronyms=["EBIT", "EBITDA", "EPS", "NI"],
            symbol=symbol,
        )

        income_statements.append(income)

    income_statements = pa.Table.from_pandas(
        pd.concat(income_statements, ignore_index=True), schema=INCOME_STATEMENTS_SCHEMA
    )

    return income_statements


def transform(
    adls: AzureDataLakeStorage,
) -> None:
    _logger.info("Starting income-statements transformation...")

    symbols = [
        "WBC.AX",
        # "CBA.AX",
        "ANZ.AX",
        # "NAB.AX",
        "MQG.AX",
    ]
    tickers = yf.Tickers(symbols)

    income_statements = _retrieve_income_statements(tickers)

    parquet_to_adls(adls, income_statements, adls.model_paths[income_statements_model.name].path)

    _logger.info("Transform completed successfully")
