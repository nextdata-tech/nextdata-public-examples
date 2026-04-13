# ruff: noqa: F403, F405
from nxd_models import *

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
                "Annual operating cash flow in millions of the company's reporting currency",
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
