# ruff: noqa: F403, F405
from nxd_models import *

cash_flows = (
    semantic_model(
        name="cash_flows",
        description="Cash flow metrics for publicly listed companies, as reported in Yahoo Finance's financial data.",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "metric": (
                string(),
                "Name of the cash flow line item (e.g., 'Operating Cash Flow', 'Capital Expenditure').",
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

balance_sheets = (
    semantic_model(
        name="balance_sheets",
        description="Balance sheet metrics for publicly listed companies, "
        "as reported in Yahoo Finance's financial data.",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "metric": (
                string(),
                "Name of the balance sheet line item (e.g., 'Total Capitalization', 'Total Debt').",
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

source_documents = (
    semantic_model(
        name="source_documents",
        description="References to the source documents.",
    )
    .schema(
        {
            "id": (
                int32(),
                "Identifier for the record.",
            ),
            "filename": (
                string(),
                "Name of the file.",
            ),
            "document_type": (
                string(),
                "Document type.",
            ),
            "url": (
                string(),
                "Reference to the source document.",
            ),
        }
    )
    .document_collection()
)
