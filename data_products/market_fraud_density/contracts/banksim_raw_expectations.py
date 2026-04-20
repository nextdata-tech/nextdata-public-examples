"""
Input expectation contract for the raw BankSim1 Kaggle source.

Validates that the data arriving from the Kaggle API (ealaxi/banksim1) meets
the minimum structural and quality requirements before the transform runs.

Checks
------
1. required_columns   – all expected CSV columns are present.
2. zero_null_category – `category` column has no null / empty values.
3. zero_null_fraud    – `fraud` column has no null values.
4. non_negative_amount – `amount` is non-negative for every row.
5. known_categories   – every category (after stripping quotes and es_ prefix)
                        maps to a known BankSim1 market type.
"""

import pandas as pd
from nxd.core.context import S3Input
from nxd.core.policy import VerifyResult
from nxd.spec import Model

REQUIRED_COLUMNS = {
    "step",
    "customer",
    "age",
    "gender",
    "zipcodeOri",
    "merchant",
    "zipMerchant",
    "category",
    "amount",
    "fraud",
}

KNOWN_CATEGORIES = {
    "barsandrestaurants",
    "contents",
    "fashion",
    "food",
    "health",
    "home",
    "hotelservices",
    "hyper",
    "leisure",
    "otherservices",
    "sportsandtoys",
    "tech",
    "transportation",
    "travel",
    "wellnessandbeauty",
}


def check_banksim_raw_expectations(input: S3Input, models: dict[str, Model]) -> VerifyResult:
    model = models.get("banksim_raw_model")
    if model is None:
        return VerifyResult.failure("banksim_raw_model not found in provided models")

    df: pd.DataFrame = model.to_pandas()

    # Checks Required columns present in the data
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        return VerifyResult.failure(f"required_columns: source CSV is missing columns: {sorted(missing_cols)}")

    # Checks for Zero-null on category
    null_category = df["category"].isna().sum() + (df["category"].astype(str).str.strip() == "").sum()
    if null_category > 0:
        return VerifyResult.failure(f"zero_null_category: {null_category} row(s) have null or empty category")

    # Checks for Zero-null on fraud
    null_fraud = df["fraud"].isna().sum()
    if null_fraud > 0:
        return VerifyResult.failure(f"zero_null_fraud: {null_fraud} row(s) have null fraud flag")

    # Checks for Non-negative amount
    neg_amount = (pd.to_numeric(df["amount"], errors="coerce").fillna(0) < 0).sum()
    if neg_amount > 0:
        return VerifyResult.failure(f"non_negative_amount: {neg_amount} row(s) have negative transaction amount")

    # Checks for Known categories
    normalised = (
        df["category"].astype(str).str.strip().str.strip("'\"").str.replace(r"^es_", "", regex=True).str.lower()
    )
    unknown = set(normalised.unique()) - KNOWN_CATEGORIES
    if unknown:
        return VerifyResult.failure(f"known_categories: unexpected category values found: {sorted(unknown)}")

    return VerifyResult.success()
