import logging
from collections import defaultdict

import pyarrow as pa
from models import anomalies as anomalies_model
from models import transactions as transactions_model
from nxd.data_product.context import AzureDataLakeStorage
from utils import adls_to_parquet
from utils import parquet_to_adls

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)


def _detect_suspicious_transactions(table: pa.Table, hours: int = 1) -> pa.Table:
    anomalies = []
    table = table.to_pylist()

    customer_groups = defaultdict(list)
    for r in table:
        customer_groups[r["customer_id"]].append(r)

    for _, transactions in customer_groups.items():
        transactions = sorted(transactions, key=lambda x: x["date"])
        window = []
        for transaction in transactions:
            # filter to transactions within the window
            window = [w for w in window if (transaction["date"] - w["date"]).total_seconds() <= hours * 3600]

            # compare transaction with transactions in the window
            for w in window:
                if transaction["country_code"] != w["country_code"]:
                    for t in [transaction, w]:
                        if t not in anomalies:
                            anomalies.append(t)

            # add transaction to window
            window.append(transaction)

    return pa.Table.from_pylist(
        anomalies,
        schema=pa.schema(
            [
                pa.field("transaction_id", pa.string()),
                pa.field("customer_id", pa.string()),
                pa.field("date", pa.timestamp("ns")),
                pa.field("country_code", pa.string()),
            ]
        ),
    ).sort_by([("customer_id", "ascending"), ("date", "ascending")])


def transform(
    credit_card_tx: AzureDataLakeStorage,
    adls: AzureDataLakeStorage,
) -> None:
    _logger.info("Starting suspicious-tx transformation...")

    transactions = adls_to_parquet(credit_card_tx, credit_card_tx.model_paths[transactions_model.name].path)
    transactions = transactions.select(["transaction_id", "customer_id", "date", "country_code"])

    anomalies = _detect_suspicious_transactions(
        transactions,
        hours=1,
    )

    parquet_to_adls(adls, anomalies, adls.model_paths[anomalies_model.name].path)

    _logger.info("Transform completed successfully")
