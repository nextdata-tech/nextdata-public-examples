# ruff: noqa: F403, F405
from nxd_models import *

# Input models — define the expected schema of upstream data product outputs.

announcements = (
    semantic_model(
        name="announcements",
        description="Dataset containing company announcements released to the National Association of Securities Dealers Automated Quotations (NASDAQ), including metadata, associated companies, and document details.",
    )
    .sampling(method=SamplingMethod.Random)
    .schema(
        {
            "date": (
                timestamp(unit=DurationUnit.Nanoseconds),
                "Date and time the announcement was released to the NASDAQ, in nanosecond precision.",
            ),
            "document_key": (
                string(),
                "Unique identifier for the announcement document within the NASDAQ or storage system.",
            ),
            "file_size": (
                string(),
                "Size of the announcement document file, typically expressed in bytes or a human-readable format.",
            ),
            "full_path": (
                string(),
                "Full file path where the announcement document is stored or can be retrieved.",
            ),
            "headline": (
                string(),
                "Headline or title of the announcement, summarising its content.",
            ),
            "is_price_sensitive": (
                boolean(),
                "Indicates whether the announcement is classified as price-sensitive under NASDAQ rules.",
            ),
            "path": (
                string(),
                "Relative file path where the announcement document is stored or can be retrieved.",
            ),
            "symbol": (
                string(),
                "Primary NASDAQ ticker symbol of the company issuing the announcement.",
            ),
            "url": (
                string(),
                "Full web address where the announcement document can be accessed or downloaded.",
            ),
        }
    )
)

income_statements = (
    semantic_model(
        name="income_statements",
        description="Income statement metrics for publicly listed companies, as reported in Yahoo Finance's financial data.",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "date": (
                timestamp(unit=DurationUnit.Nanoseconds),
                "End date of the reporting period for the metric, expressed in nanosecond precision.",
            ),
            "metric": (
                string(),
                "Name of the income statement line item (e.g., 'Total Revenue', 'Net Income').",
            ),
            "symbol": (
                string(),
                "Ticker symbol of the company or security the income statement belongs to.",
            ),
            "value": (
                float64(),
                "Numeric value of the metric in the company's reporting currency.",
            ),
        }
    )
)

history = (
    semantic_model(
        name="history",
        description="Historical price and trading volume data for a financial instrument retrieved from the Yahoo Finance API.",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "close": (
                float64(),
                "Closing price of the security for the given date.",
            ),
            "date": (
                timestamp(unit=DurationUnit.Nanoseconds),
                "Date and time of the trading session, expressed in nanosecond precision.",
            ),
            "dividends": (
                float64(),
                "Cash dividend amount per share paid on the given date, if applicable.",
            ),
            "high": (
                float64(),
                "Highest traded price of the security during the trading session.",
            ),
            "low": (
                float64(),
                "Lowest traded price of the security during the trading session.",
            ),
            "open": (
                float64(),
                "Opening price of the security for the given date.",
            ),
            "stock_splits": (
                float64(),
                "Split ratio for any stock split that occurred on the given date (e.g., 2.0 for a 2-for-1 split).",
            ),
            "symbol": (
                string(),
                "Ticker symbol of the security or instrument (e.g., 'AAPL' for Apple Inc.).",
            ),
            "volume": (
                int64(),
                "Total number of shares or contracts traded during the session.",
            ),
        }
    )
)

# Output models

documents = (
    semantic_model(
        name="documents",
        description="Processed records, also stored as vectors within Pinecone",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "type": (
                string(),
                "Type of record processed",
            ),
            "page_content": (
                string(),
                "Contents of the record processed",
            ),
            "metadata": (
                string(),
                "Additional metadata for each record",
            ),
        }
    )
)

growth = (
    semantic_model(
        name="growth",
        description="Integrated model combining annual stock market performance (returns) with company profitability metrics (revenue and net income), enabling analysis of the relationship between financial growth and shareholder returns.",
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
                "End of the reporting period or trading year, expressed in nanoseconds precision.",
            ),
            "close": (
                float64(),
                "Closing price of the security at the end of the reporting period.",
            ),
            "annual_return": (
                float64(),
                "Year-over-year percentage change in the closing price of the security, representing annual total return (excluding dividends unless adjusted).",
            ),
            "net_income": (
                float64(),
                "Net income reported by the company for the fiscal year, in the company's reporting currency.",
            ),
            "total_revenue": (
                float64(),
                "Total revenue reported by the company for the fiscal year, in the company's reporting currency.",
            ),
            "revenue_growth": (
                float64(),
                "Year-over-year growth rate of total revenue, computed as the percentage change compared to the prior fiscal year.",
            ),
            "net_income_growth": (
                float64(),
                "Year-over-year growth rate of net income, computed as the percentage change compared to the prior fiscal year.",
            ),
        }
    )
    .link(
        "symbol",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/income-statements#/models/income_statements/attributes/symbol",
    )
    .link(
        "date",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/income-statements#/models/income_statements/attributes/date",
    )
    .link(
        "close",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/stock-history#/models/history/attributes/close",
    )
)

dividend_sustainability = (
    semantic_model(
        name="dividend_sustainability",
        description="Year-over-year dividend sustainability analysis comparing dividend per share growth against operating cash flow growth trends for financial institutions",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "bank": (
                string(),
                "Bank identifier or ticker symbol (e.g. CBA, ANZ, WBC, NAB)",
            ),
            "year": (
                int32(),
                "Fiscal year for the dividend and cash flow data",
            ),
            "dividend_per_share": (
                decimal(4, 2),
                "Total annual dividend per share paid during the year (sum of interim and final dividends)",
            ),
            "operating_cash_flow_thousands": (
                float64(),
                "Annual operating cash flow in thousands of the company's reporting currency",
            ),
            "dividend_yield_trend": (
                float64(),
                "Year-over-year percentage change in dividend per share compared to previous year. Null for first year of data",
            ),
            "ocf_trend": (
                float64(),
                "Year-over-year percentage change in operating cash flow compared to previous year. Null for first year of data",
            ),
            "dividend_growth_vs_ocf_growth": (
                float64(),
                "Differential between dividend growth rate and OCF growth rate. Positive values indicate dividend growth exceeds OCF growth. Null for first year of data",
            ),
            "sustainability_flag": (
                string(),
                "Categorical assessment of dividend sustainability based on growth differential - GROWING FASTER THAN OCF, MODERATE GROWTH, or CONSERVATIVE GROWTH",
            ),
        }
    )
    .link(
        "bank",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/company-dividends#/models/dividends/attributes/bank",
    )
    .link(
        "dividend_per_share",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/company-dividends#/models/dividends/attributes/dividend_per_share",
    )
    .link(
        "operating_cash_flow_thousands",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/financial-statements#/models/cash_flows/attributes/value",
    )
)
