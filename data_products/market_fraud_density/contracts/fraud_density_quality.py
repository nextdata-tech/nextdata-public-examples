"""
Contract: fraud_density_quality

Enforces the following promises on the fraud_density_model output:
  • Zero-Null  – market_type must have no null / empty values (Acceptance Criterion 4).
  • Uniqueness – market_type is the Primary Key; no duplicate categories allowed.
  • Range      – fraud_rate_pct must be in [0.0, 100.0].
  • Completeness – transaction_count must be > 0 in every row (Acceptance Criterion 3).
"""

import csv
import io
import logging
import urllib.request

from nxd import data_product
from nxd.data_product.context import Model
from nxd.data_product.context import S3Input
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum

_logger = logging.getLogger("contracts.fraud_density_quality")
_logger.setLevel(logging.INFO)


def read_csv(s3: S3Input, model_name: str) -> list[dict]:
    model_urls = getattr(s3, "model_urls", None)
    if not model_urls:
        raise RuntimeError("S3Input.model_urls is not available.")
    url = model_urls.get(model_name)
    if not url:
        raise KeyError(f"No URL for model '{model_name}' in model_urls (available: {list(model_urls.keys())})")
    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def check_fraud_density_quality(input: S3Input, models: dict[str, Model]) -> VerifyResult:
    """Validate the fraud_density_model output against all acceptance criteria."""
    try:
        model_name = next(iter(models)) if models else "fraud_density_model"
        rows = read_csv(input, model_name)
        errors: list[str] = []

        if not rows:
            return VerifyResult(
                VerifyResultEnum.FAILED,
                {"result": "Promise failed. Output has zero rows."},
            )

        columns = set(rows[0].keys())
        required_columns = {"market_type", "transaction_count", "fraud_event_count", "fraud_rate_pct"}
        missing_cols = required_columns - columns
        if missing_cols:
            return VerifyResult(
                VerifyResultEnum.FAILED,
                {
                    "result": "Promise failed. Required columns are missing.",
                    "missing_columns": sorted(missing_cols),
                },
            )

        # Zero-Null check on market_type (Acceptance Criterion 4)
        null_market = [i for i, r in enumerate(rows) if not str(r.get("market_type", "")).strip()]
        if null_market:
            errors.append(f"market_type has {len(null_market)} null/empty value(s) at row indices: {null_market[:5]}")

        # Uniqueness — market_type is the Primary Key (Expectation: no duplicates)
        seen: set[str] = set()
        duplicates: set[str] = set()
        for r in rows:
            mt = str(r.get("market_type", "")).strip().lower()
            if mt in seen:
                duplicates.add(mt)
            seen.add(mt)
        if duplicates:
            errors.append(f"market_type uniqueness violated for: {sorted(duplicates)}")

        # Completeness — transaction_count > 0 (Acceptance Criterion 3)
        zero_tx = [r["market_type"] for r in rows if (to_int(r.get("transaction_count")) or 0) <= 0]
        if zero_tx:
            errors.append(f"transaction_count <= 0 for categories: {zero_tx[:5]}")

        # Range check — fraud_rate_pct in [0.0, 100.0]
        out_of_range = [
            r["market_type"]
            for r in rows
            if (v := to_float(r.get("fraud_rate_pct"))) is not None and not (0.0 <= v <= 100.0)
        ]
        if out_of_range:
            errors.append(f"fraud_rate_pct out of [0.0, 100.0] for categories: {out_of_range[:5]}")

        if errors:
            _logger.warning("Fraud density quality check failed: %s", errors)
            return VerifyResult(
                VerifyResultEnum.FAILED,
                {
                    "result": "Promise failed. Data quality checks did not pass.",
                    "errors": errors,
                    "row_count": len(rows),
                },
            )

        _logger.info("Fraud density quality check passed: %d categories.", len(rows))
        return VerifyResult(
            VerifyResultEnum.PASS,
            {
                "result": "Promise fulfilled. All quality checks passed.",
                "row_count": len(rows),
                "market_types_verified": sorted(r.get("market_type", "") for r in rows),
            },
        )

    except Exception as e:
        _logger.exception("Unexpected error during fraud density quality check.")
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {"result": f"Promise failed. Unexpected error: {e}"},
        )


if __name__ == "__main__":

    @data_product.on_verify()
    def verify(input: S3Input, models: dict[str, Model]) -> VerifyResult:
        return check_fraud_density_quality(input, models)

    data_product.verify()
