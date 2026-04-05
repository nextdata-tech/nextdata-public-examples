"""
Local test script for _retrieve_cash_flows function debugging.
"""

import logging
import sys

import pandas as pd
import pyarrow as pa
import yfinance as yf

# Add the module to path
sys.path.insert(0, "../financial_statements")


# Setup logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _format_financial_report_dataframe(
    dataframe: pd.DataFrame, symbol: str, acronyms: list[str] | None = None
) -> pd.DataFrame:
    """Format financial report dataframe."""
    logger.info(f"Formatting dataframe for symbol: {symbol}")
    logger.debug(f"Input dataframe shape: {dataframe.shape}")
    logger.debug(f"Input dataframe index: {dataframe.index.tolist()[:5]}...")

    dataframe.index = yf.utils.camel2title(dataframe.index, sep="_", acronyms=acronyms)
    dataframe.index = dataframe.index.str.lower()

    dataframe = dataframe.reset_index(names="metric")
    print(dataframe.head())

    # Convert all column names to strings (yfinance returns datetime column names)
    dataframe.columns = dataframe.columns.astype(str)

    dataframe = dataframe.melt(
        id_vars="metric",
        var_name="date",
        value_name="value",
    )
    dataframe["date"] = pd.to_datetime(dataframe["date"])
    dataframe["symbol"] = symbol

    logger.debug(f"Output dataframe shape: {dataframe.shape}")
    logger.debug(f"Output dataframe columns: {dataframe.columns.tolist()}")

    return dataframe


def _retrieve_cash_flows(tickers: yf.Tickers) -> pa.Table:
    """Retrieve cash flows from tickers."""
    logger.info(f"Retrieving cash flows for {len(tickers.tickers)} tickers")

    cash_flows: list[pd.DataFrame] = []

    for symbol, ticker in tickers.tickers.items():
        logger.info(f"Processing symbol: {symbol}")
        try:
            cash = ticker.get_cash_flow(pretty=False, freq="yearly")
            logger.debug(f"Cash flow type: {type(cash)}")

            if isinstance(cash, dict):
                raise TypeError(f"Cash flow returned as dict by yfinance for symbol - {symbol}")

            if cash is None or cash.empty:
                logger.warning(f"Empty or None cash flow for symbol: {symbol}")
                continue

            logger.debug(f"Cash flow shape: {cash.shape}")

            cash = _format_financial_report_dataframe(
                cash,
                acronyms=["PPE"],
                symbol=symbol,
            )

            cash_flows.append(cash)
            logger.info(f"✓ Successfully processed {symbol}")

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
            raise

    if not cash_flows:
        logger.error("No cash flows collected!")
        raise ValueError("No cash flow data retrieved for any ticker")

    logger.info(f"Concatenating {len(cash_flows)} dataframes")
    combined = pd.concat(cash_flows, ignore_index=True)
    logger.debug(f"Combined dataframe shape: {combined.shape}")
    logger.debug(f"Combined dataframe sample:\n{combined.head()}")

    cash_flows_table = pa.Table.from_pandas(combined)
    logger.info(f"Converted to PyArrow table with schema: {cash_flows_table.schema}")

    return cash_flows_table


def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("Starting cash flows retrieval test")
    logger.info("=" * 60)

    symbols = [
        "WBC.AX",
        "ANZ.AX",
        "MQG.AX",
    ]

    logger.info(f"Testing with symbols: {symbols}")

    try:
        logger.info("Creating Tickers object...")
        tickers = yf.Tickers(symbols)
        logger.info(f"✓ Tickers created: {list(tickers.tickers.keys())}")

        logger.info("Calling _retrieve_cash_flows...")
        cash_flows_table = _retrieve_cash_flows(tickers)

        logger.info("=" * 60)
        logger.info("✅ SUCCESS!")
        logger.info("=" * 60)
        logger.info(f"Result type: {type(cash_flows_table)}")
        logger.info(f"Table shape: {cash_flows_table.num_rows} rows, {cash_flows_table.num_columns} columns")
        logger.info(f"Schema: {cash_flows_table.schema}")
        logger.info(f"Column names: {cash_flows_table.column_names}")
        logger.info("\nFirst few rows:")
        logger.info(cash_flows_table.to_pandas().head(10))

        return True

    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ FAILED!")
        logger.error("=" * 60)
        logger.error(f"Error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
