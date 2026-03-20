# ruff: noqa: F403, F405
from nxd_models import *

# Model 1: raw BankSim1 transactions
banksim_transactions_model = semantic_model(
    name="banksim_transactions_model",
    description=(
        "Cleaned BankSim1 raw transaction stream. One row per transaction. "
        "Single-quoted identifiers stripped. Column names normalized to snake_case."
    ),
).schema(
    {
        "step": (int64(), "Simulation time step"),
        "customer": (string(), "Customer identifier"),
        "age": (string(), "Customer age bracket (0=≤18 … 6=>65)"),
        "gender": (string(), "Customer gender (M / F)"),
        "zipcode_ori": (string(), "Customer origin zip code"),
        "merchant": (string(), "Merchant identifier"),
        "zip_merchant": (string(), "Merchant zip code"),
        "category": (string(), "Raw merchant category (includes es_ prefix)"),
        "amount": (float64(), "Transaction amount"),
        "fraud": (boolean(), "True if the transaction is fraudulent"),
    }
)

# Model 2: aggregated fraud density by market category
fraud_density_model = (
    semantic_model(
        name="fraud_density_model",
        description=(
            "Consolidated fraud density metrics aggregated by merchant category (Market Type). "
            "One row per unique normalized market category. No PII included."
        ),
    )
    .schema(
        {
            "market_type": (string(), "Normalized merchant category (e.g. 'transportation', 'food')"),
            "transaction_count": (int64(), "Total number of transactions recorded for this market"),
            "fraud_event_count": (int64(), "Total number of confirmed fraudulent transactions"),
            "fraud_rate_pct": (float64(), "Percentage of transactions that were fraudulent (0.0 – 100.0)"),
        }
    )
    .link(
        "market_type",
        Predicate.GlossaryTerm,
        "https://app.partner.nextopia.dev/data-product/demo/fraud-analytics-glossary#/terms/market_type",
    )
    .link(
        "fraud_rate_pct",
        Predicate.GlossaryTerm,
        "https://app.partner.nextopia.dev/data-product/demo/fraud-analytics-glossary#/terms/fraud_rate_pct",
    )
)
