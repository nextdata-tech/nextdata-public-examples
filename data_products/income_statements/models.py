# ruff: noqa: F403, F405
from nxd_models import *

income_statements = (
    semantic_model(
        name="income_statements",
        description="Income statement metrics for publicly listed companies, "
        "as reported in Yahoo Finance's financial data.",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "metric": (
                string(),
                "Name of the income statement line item (e.g., 'Total Revenue', 'Net Income').",
            ),
            "date": (
                timestamp(unit=DurationUnit.Nanoseconds),
                "End date of the reporting period for the metric, expressed in nanosecond precision.",
            ),
            "value": (
                float64(),
                "Numeric value of the metric in the company's reporting currency.",
            ),
            "symbol": (
                string(),
                "Ticker symbol of the company or security the income statement belongs to.",
            ),
        }
    )
)
