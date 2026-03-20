"""
Contract: banksim_transactions_quality

Enforces the "Zero Null" expectation (Acceptance Criterion 4) on the
banksim_transactions_model before it is published:
  • category  must have no null / empty values.
  • fraud     must have no null values and only boolean-like entries.
  • amount    must be non-negative.
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

_logger = logging.getLogger("contracts.banksim_transactions_quality")
_logger.setLevel(logging.INFO)

VALID_FRAUD_VALUES = {"true", "false", "1", "0"}


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


def check_banksim_transactions_quality(input: S3Input, models: dict[str, Model]) -> VerifyResult:
    """Zero-Null + non-negative amount check on the raw transaction model."""
    try:
        model_name = next(iter(models)) if models else "banksim_transactions_model"
        rows = read_csv(input, model_name)
        errors: list[str] = []

        if not rows:
            return VerifyResult(
                VerifyResultEnum.FAILED,
                {"result": "Promise failed. Output has zero rows."},
            )

        # Zero-Null: category
        null_category = sum(1 for r in rows if not str(r.get("category", "")).strip())
        if null_category:
            errors.append(f"category has {null_category} null/empty value(s).")

        # Zero-Null: fraud
        null_fraud = sum(1 for r in rows if str(r.get("fraud", "")).strip().lower() not in VALID_FRAUD_VALUES)
        if null_fraud:
            errors.append(
                f"fraud has {null_fraud} row(s) with null or unrecognised values "
                f"(expected one of {VALID_FRAUD_VALUES})."
            )

        # Non-negative amount
        try:
            neg_amount = sum(1 for r in rows if float(r.get("amount", 0) or 0) < 0)
            if neg_amount:
                errors.append(f"amount has {neg_amount} negative value(s).")
        except ValueError:
            errors.append("amount column contains non-numeric values.")

        if errors:
            _logger.warning("Banksim transactions quality check failed: %s", errors)
            return VerifyResult(
                VerifyResultEnum.FAILED,
                {
                    "result": "Promise failed. Zero-null / quality checks did not pass.",
                    "errors": errors,
                    "row_count": len(rows),
                },
            )

        _logger.info("Banksim transactions quality check passed: %d rows.", len(rows))
        return VerifyResult(
            VerifyResultEnum.PASS,
            {
                "result": "Promise fulfilled. All zero-null and quality checks passed.",
                "row_count": len(rows),
            },
        )

    except Exception as e:
        _logger.exception("Unexpected error during banksim transactions quality check.")
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {"result": f"Promise failed. Unexpected error: {e}"},
        )


if __name__ == "__main__":

    @data_product.on_verify()
    def verify(input: S3Input, models: dict[str, Model]) -> VerifyResult:
        return check_banksim_transactions_quality(input, models)

    data_product.verify()
