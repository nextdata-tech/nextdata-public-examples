# ruff: noqa: F403, F405
from nxd_models import *

companies = (
    semantic_model(
        name="companies",
        description="Companies listed on the National Association of Securities Dealers Automated Quotations (NASDAQ)",
    )
    .sampling(method=SamplingMethod.Random)
    .schema(
        {
            "asx_code": (
                string(),
                "The stock ticker symbol used to uniquely identify the company on the NASDAQ",
            ),
            "company_name": (
                string(),
                "The official name of the company as listed on the NASDAQ",
            ),
            "gics_industry_group": (
                string(),
                "The Global Industry Classification Standard (GICS) industry group to which the company belongs",
            ),
            "listing_date": (
                date32(),
                "The date the company's shares were first listed on the ASX",
            ),
            "market_cap": (
                string(),
                "The company's market capitalisation — the total value of its outstanding shares at the time of data collection - whole American dollars",
            ),
        }
    )
)

announcements = (
    semantic_model(
        name="announcements",
        description="Dataset containing company announcements released to the National Association of Securities "
        "Dealers Automated Quotations (NASDAQ), "
        "including metadata, associated companies, and document details.",
    )
    .sampling(method=SamplingMethod.Random)
    .schema(
        {
            "path": (
                string(),
                "Relative file path where the announcement document is stored or can be retrieved.",
            ),
            "full_path": (
                string(),
                "Full file path where the announcement document is stored or can be retrieved.",
            ),
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
            "headline": (
                string(),
                "Headline or title of the announcement, summarising its content.",
            ),
            "is_price_sensitive": (
                boolean(),
                "Indicates whether the announcement is classified as price-sensitive under NASDAQ rules.",
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
