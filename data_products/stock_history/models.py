# ruff: noqa: F403, F405
from nxd_models import *

history = (
    semantic_model(
        name="history",
        description="Historical price and trading volume data for a financial instrument "
        "retrieved from the Yahoo Finance API.",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "symbol": (
                string(),
                "Ticker symbol of the security or instrument (e.g., 'AAPL' for Apple Inc.).",
            ),
            "date": (
                timestamp(unit=DurationUnit.Nanoseconds),
                "Date and time of the trading session, expressed in nanosecond precision.",
            ),
            "open": (
                float64(),
                "Opening price of the security for the given date.",
            ),
            "high": (
                float64(),
                "Highest traded price of the security during the trading session.",
            ),
            "low": (
                float64(),
                "Lowest traded price of the security during the trading session.",
            ),
            "close": (
                float64(),
                "Closing price of the security for the given date.",
            ),
            "volume": (
                int64(),
                "Total number of shares or contracts traded during the session.",
            ),
            "dividends": (
                float64(),
                "Cash dividend amount per share paid on the given date, if applicable.",
            ),
            "stock_splits": (
                float64(),
                "Split ratio for any stock split that occurred on the given date (e.g., 2.0 for a 2-for-1 split).",
            ),
        }
    )
)
