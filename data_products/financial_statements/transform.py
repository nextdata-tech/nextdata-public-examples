import logging

import pandas as pd
import pyarrow as pa
import yfinance as yf
from models import balance_sheets as balance_sheets_model
from models import cash_flows as cash_flows_model
from models import source_documents as source_documents_model
from nxd import data_product
from nxd.data_product.context import API
from nxd.data_product.context import AzureDataLakeStorage
from nxd.data_product.context import DatabricksWrite
from pyspark.sql import SparkSession
from utils import _retrieve_source_docs
from utils import parquet_to_adls

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)

# Define explicit PyArrow schemas to match model definitions
CASH_FLOWS_SCHEMA = pa.schema(
    [
        pa.field("metric", pa.string()),
        pa.field("date", pa.timestamp("ns")),
        pa.field("value", pa.float64()),
        pa.field("symbol", pa.string()),
    ]
)

BALANCE_SHEETS_SCHEMA = pa.schema(
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


def _retrieve_cash_flows(tickers: yf.Tickers) -> pa.Table:
    cash_flows: list[pd.DataFrame] = []
    for symbol, ticker in tickers.tickers.items():
        cash = ticker.get_cash_flow(pretty=False, freq="yearly")
        if isinstance(cash, pd.Series):
            cash = cash.to_frame().T
        if isinstance(cash, dict):
            raise TypeError(f"Cash flow returned as dict by yfinance for symbol - {symbol}")

        cash = _format_financial_report_dataframe(
            cash,
            acronyms=["PPE"],
            symbol=symbol,
        )

        cash_flows.append(cash)

    cash_flows = pa.Table.from_pandas(pd.concat(cash_flows, ignore_index=True), schema=CASH_FLOWS_SCHEMA)

    return cash_flows


def _retrieve_balance_sheets(tickers: yf.Tickers) -> pa.Table:
    balance_sheets: list[pd.DataFrame] = []
    for symbol, ticker in tickers.tickers.items():
        balance = ticker.get_balance_sheet(pretty=False, freq="yearly")
        if isinstance(balance, pd.Series):
            balance = balance.to_frame().T
        if isinstance(balance, dict):
            raise TypeError(f"Balance sheet returned as dict by yfinance for symbol - {symbol}")

        balance = _format_financial_report_dataframe(
            balance,
            acronyms=["PPE"],
            symbol=symbol,
        )

        balance_sheets.append(balance)

    balance_sheets = pa.Table.from_pandas(pd.concat(balance_sheets, ignore_index=True), schema=BALANCE_SHEETS_SCHEMA)

    return balance_sheets


@data_product.on_transform()
def transform(
    spark: SparkSession,
    competitor_data_api: API,
    adls: AzureDataLakeStorage,
    databricks: DatabricksWrite,
) -> None:
    _logger.info("Starting yahoo-finance-source transformation...")

    symbols = [
        "WBC.AX",
        # "CBA.AX",
        "ANZ.AX",
        # "NAB.AX",
        "MQG.AX",
    ]
    tickers = yf.Tickers(symbols)

    cash_flows = _retrieve_cash_flows(tickers)
    balance_sheets = _retrieve_balance_sheets(tickers)
    source_documents = _retrieve_source_docs(competitor_data_api)

    parquet_to_adls(adls, cash_flows, adls.model_paths[cash_flows_model.name].path)
    parquet_to_adls(adls, balance_sheets, adls.model_paths[balance_sheets_model.name].path)
    parquet_to_adls(adls, source_documents, adls.model_paths[source_documents_model.name].path)

    for table_name, arrow_table in [("cash_flows", cash_flows), ("balance_sheets", balance_sheets)]:
        spark_df = spark.createDataFrame(arrow_table.to_pandas())
        # cast schema to match model definition - this is needed because Spark may infer different types
        if table_name == "cash_flows":
            spark_df = spark_df.select(
                spark_df["metric"].cast("string"),
                spark_df["date"].cast("timestamp_ntz"),
                spark_df["value"].cast("double"),
                spark_df["symbol"].cast("string"),
            )
        elif table_name == "balance_sheets":
            spark_df = spark_df.select(
                spark_df["metric"].cast("string"),
                spark_df["date"].cast("timestamp_ntz"),
                spark_df["value"].cast("double"),
                spark_df["symbol"].cast("string"),
            )
        fqn = databricks.full_table_name(table_name)
        spark_df.write.format("delta").mode("overwrite").saveAsTable(fqn)

    _logger.info("Transform completed successfully")


if __name__ == "__main__":
    data_product.main()
