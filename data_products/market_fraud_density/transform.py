import logging
import os
from pathlib import Path

import boto3
import kagglehub
import pandas as pd
from botocore.client import BaseClient
from botocore.config import Config as BotoConfig
from models import banksim_transactions_model
from models import fraud_density_model
from nxd.data_product.context import S3Output

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)

KAGGLE_DATASET = "ealaxi/banksim1"
KAGGLE_FILENAME = "bs140513_032310.csv"
FALLBACK_CSV = "data/bs140513_032310.csv"


def get_s3_client(ctx: S3Output) -> BaseClient:
    return boto3.client(
        "s3",
        aws_access_key_id=ctx.aws_access_key_id,
        aws_secret_access_key=ctx.aws_secret_access_key,
        config=BotoConfig(region_name=ctx.region_name),
    )


def fetch_from_kaggle() -> pd.DataFrame:
    api_token = os.environ.get("KAGGLE_API")
    if api_token:
        os.environ["KAGGLE_API_TOKEN"] = api_token

    _logger.info("Downloading BankSim1 via kagglehub: %s", KAGGLE_DATASET)
    dataset_path = kagglehub.dataset_download(KAGGLE_DATASET)
    _logger.info("Dataset downloaded to: %s", dataset_path)

    csv_path = Path(dataset_path) / KAGGLE_FILENAME
    if not csv_path.exists():
        # Search recursively in case kagglehub places it in a sub-directory
        matches = list(Path(dataset_path).rglob(KAGGLE_FILENAME))
        if not matches:
            raise FileNotFoundError(f"'{KAGGLE_FILENAME}' not found under kagglehub download path: {dataset_path}")
        csv_path = matches[0]

    df = pd.read_csv(csv_path)
    _logger.info("Kaggle batch loaded: %d raw transactions from %s", len(df), csv_path)
    return df


def read_source_data() -> pd.DataFrame:
    try:
        return fetch_from_kaggle()
    except Exception as exc:
        _logger.warning("kagglehub fetch failed (%s). Falling back to local CSV.", exc)

    path = Path(os.environ.get("SOURCE_CSV_PATH", FALLBACK_CSV))
    if not path.exists():
        raise FileNotFoundError(
            f"Source CSV not found at '{path}'. "
            "Set SOURCE_CSV_PATH or supply KAGGLE_USERNAME / KAGGLE_KEY for kagglehub."
        )
    df = pd.read_csv(path)
    _logger.info("Read %d rows from local CSV: %s", len(df), path)
    return df


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    str_cols = ["customer", "age", "gender", "zipcodeOri", "merchant", "zipMerchant", "category"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip("'").str.strip()

    df = df.rename(columns={"zipcodeOri": "zipcode_ori", "zipMerchant": "zip_merchant"})

    if "step" in df.columns:
        df["step"] = pd.to_numeric(df["step"], errors="coerce").fillna(0).astype(int)
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if "fraud" in df.columns:
        df["fraud"] = pd.to_numeric(df["fraud"], errors="coerce").fillna(0).astype(int).astype(bool)

    schema_cols = [
        "step",
        "customer",
        "age",
        "gender",
        "zipcode_ori",
        "merchant",
        "zip_merchant",
        "category",
        "amount",
        "fraud",
    ]
    for col in schema_cols:
        if col not in df.columns:
            df[col] = None
    return df[schema_cols]


def aggregate_fraud_density(df: pd.DataFrame) -> pd.DataFrame:
    """Transform raw BankSim1 transactions into the fraud_density_model schema.

    Steps
    -----
    1. Validate required columns (``category``, ``fraud``).
    2. Normalize category: strip the 'es_' Enterprise/Simulation prefix artifact.
    3. Coerce ``fraud`` to integer (1 / 0).
    4. GROUP BY market_type — COUNT(*) and SUM(fraud).
    5. Drop any category with zero transactions.
    6. Compute fraud_rate_pct = (fraud_event_count / transaction_count) * 100.
    7. Sort descending by fraud_rate_pct (highest relative risk first).
    """
    required = {"category", "fraud"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Source data is missing required columns: {missing}")

    df = df.copy()

    df["market_type"] = (
        df["category"].str.strip().str.strip("'\"").str.replace(r"^es_", "", regex=True).str.strip().str.lower()
    )

    df["fraud"] = pd.to_numeric(df["fraud"], errors="coerce").fillna(0).astype(int)

    grouped = df.groupby("market_type", as_index=False).agg(
        transaction_count=("fraud", "count"),
        fraud_event_count=("fraud", "sum"),
    )

    grouped = grouped[grouped["transaction_count"] > 0].copy()

    grouped["fraud_rate_pct"] = (grouped["fraud_event_count"] * 100.0 / grouped["transaction_count"]).round(2)

    return grouped.sort_values("fraud_rate_pct", ascending=False).reset_index(drop=True)


def _write_model(client, bucket: str, key: str, df: pd.DataFrame, label: str) -> None:
    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=df.to_csv(index=False),
            ContentType="text/csv",
        )
        _logger.info("Wrote %d rows → s3://%s/%s  [%s]", len(df), bucket, key, label)
    except Exception as e:
        _logger.exception("Failed to write %s to object storage.", label)
        raise RuntimeError(f"Error saving '{label}' to bucket '{bucket}' key '{key}'") from e


def transform(object_storage: S3Output) -> None:
    _logger.info("Starting market-fraud-density transform (simulated streaming batch)...")

    df_raw = read_source_data()
    client = get_s3_client(object_storage)

    # Model 1: raw cleaned transactions
    df_tx = clean_transactions(df_raw)
    _logger.info("Cleaned %d raw transactions.", len(df_tx))
    _write_model(
        client,
        object_storage.bucket,
        object_storage.model_output_paths[banksim_transactions_model.name],
        df_tx,
        "banksim_transactions_model",
    )

    # Model 2: aggregated fraud density per market category
    df_agg = aggregate_fraud_density(df_raw)
    _logger.info(
        "Aggregated %d market categories | fraud events: %d / %d total transactions.",
        len(df_agg),
        int(df_agg["fraud_event_count"].sum()),
        int(df_agg["transaction_count"].sum()),
    )
    _write_model(
        client,
        object_storage.bucket,
        object_storage.model_output_paths[fraud_density_model.name],
        df_agg,
        "fraud_density_model",
    )
