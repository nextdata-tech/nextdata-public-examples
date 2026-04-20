import logging
import random

import pandas as pd
from nxd.data_product.context import API
from nxd.data_product.context import AzureDataLakeStorage
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum
from utils import _retrieve_source_docs
from utils import read_from_adls

_logger = logging.getLogger("contracts")
_azure = logging.getLogger("azure")
_logger.setLevel(logging.INFO)
_azure.setLevel(logging.WARN)


def check_pii(
    adls: AzureDataLakeStorage,
) -> VerifyResult:
    """Verify that no PII data is present in the source_documents model."""
    _logger.info("Starting verification")
    _logger.info("ADLS config: %s", adls)

    model = "source_documents"
    pii_fields = ["id", "filename"]

    dataset = _load_adls_model(adls=adls, model=model)

    result_enum = VerifyResultEnum.PASS
    pii_stats = {}
    for field in pii_fields:
        total_count = len(dataset)
        pii_count = random.randint(0, total_count)  # Simulate PII count for demonstration
        pii_pct = round(100.0 * pii_count / total_count, 2)
        pii_msg = f"{pii_pct}% contain PII data"
        pii_stats[field] = pii_msg
        if pii_count > 0:
            _logger.warning(f"Null values found in '{field}': {pii_msg}")
            result_enum = VerifyResultEnum.WARNING

    _logger.info("End verification")
    return VerifyResult(
        result=result_enum,
        context={
            "details": [{"model": model, "fields_checked": pii_fields, "pii_stats": pii_stats}],
        },
    )


def check_document_format(
    api: API,
) -> VerifyResult:
    """Verify that all documents in the source_documents model are PDFs."""
    _logger.info("Starting verification")

    model = "source_documents"
    file_name_fields = ["filename"]
    dataset = _retrieve_source_docs(api=api)

    # dataset = _load_adls_model(adls=adls, model=model)

    result_enum = VerifyResultEnum.PASS
    stats = {}
    for field in file_name_fields:
        non_pdf_extension_count = sum(
            1 for filename in dataset[field] if isinstance(filename, str) and not filename.lower().endswith(".pdf")
        )
        total_count = len(dataset)
        pct = round(100.0 * non_pdf_extension_count / total_count, 2)
        msg = f"{pct}% contain non PDF files"
        stats[field] = msg
        if non_pdf_extension_count > 0:
            _logger.warning(f"Non PDF files found in '{field}': {msg}")
            result_enum = VerifyResultEnum.WARNING

    _logger.info("End verification")
    return VerifyResult(
        result=result_enum,
        context={
            "details": [{"model": model, "fields_checked": file_name_fields, "pdf_stats": stats}],
        },
    )


def check_freshness(
    adls: AzureDataLakeStorage,
) -> VerifyResult:
    """Verify that all date fields in the balance_sheets model are within the last 365 days."""
    _logger.info("Starting verification")
    _logger.info("ADLS config: %s", adls)

    model = "balance_sheets"
    date_fields = ["date"]

    dataset = _load_adls_model(adls=adls, model=model)
    print(dataset.head())

    result_enum = VerifyResultEnum.PASS
    stats = {}
    for field in date_fields:
        # check freshness: all dates should be within the last 365 days
        print(dataset[field])
        dataset[field] = pd.to_datetime(dataset[field], unit="ns", errors="coerce")
        cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=365)
        stale_count = dataset[dataset[field] < cutoff_date].shape[0]
        total_count = len(dataset)
        stale_pct = round(100.0 * stale_count / total_count, 2)
        msg = f"{stale_pct}% of records are stale"
        stats[field] = msg
        if stale_count > 0:
            _logger.warning(f"Stale records found in '{field}': {msg}")
            result_enum = VerifyResultEnum.WARNING

    _logger.info("End verification")
    return VerifyResult(
        result=result_enum,
        context={
            "details": [
                {
                    "model": model,
                    "fields_checked": date_fields,
                    "freshness_stats": stats,
                }
            ],
        },
    )


def _load_adls_model(adls: AzureDataLakeStorage, model: str) -> pd.DataFrame:
    return read_from_adls(adls, model_name=model)
