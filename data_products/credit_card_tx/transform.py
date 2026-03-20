import logging
from datetime import datetime

import pyarrow as pa
from faker import Faker
from models import customers as customers_model
from models import transactions as transactions_model
from nxd.data_product.context import AzureDataLakeStorage
from utils import adls_to_parquet
from utils import parquet_to_adls

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)


def transform(
    adls: AzureDataLakeStorage,
) -> None:
    _logger.info("Starting credit-card-tx transformation...")

    transactions = []
    customers = []

    # find any existing files
    try:
        transactions.append(
            adls_to_parquet(adls, adls.model_paths[transactions_model.name].path)
        )
        customers.append(
            adls_to_parquet(adls, adls.model_paths[customers_model.name].path)
        )
        _logger.info(
            "Existing `transactions` and `customers` .parquet files found, appending data..."
        )
    except FileNotFoundError:
        _logger.info(
            "No existing `transactions` and `customers` .parquet files found, creating new files..."
        )
        pass

    fake = Faker("en_AU")
    transactions_pylist = []
    customers_pylist = []

    for customer in [fake.uuid4() for _ in range(10)]:

        def generate_transaction(customer_id: str) -> dict:
            transaction_type = fake.random_element(
                ["deposit", "withdrawal", "transfer", "payment"]
            )
            return {
                "transaction_id": fake.uuid4(),
                "customer_id": customer_id,
                "date": fake.date_time_between(
                    start_date=datetime(2025, 1, 1),
                ),
                "type": transaction_type,
                "amount": fake.random_int(100, 10000),
                "merchant": (
                    fake.company()
                    if transaction_type in ["withdrawal", "payment"]
                    else None
                ),
                "country_code": "AU",  # fix to Australia
            }

        transactions_pylist.extend([generate_transaction(customer) for _ in range(100)])
        customers_pylist.append(
            {
                "customer_id": customer,
                # only store email domain due to pii
                "email": fake.free_email_domain(),
                # "email": fake.free_email(),  # will fail pii_compliance promise
            }
        )

    transactions.append(pa.Table.from_pylist(transactions_pylist))
    customers.append(pa.Table.from_pylist(customers_pylist))

    transactions = pa.concat_tables(transactions)
    customers = pa.concat_tables(customers)

    parquet_to_adls(adls, transactions, adls.model_paths[transactions_model.name].path)
    parquet_to_adls(adls, customers, adls.model_paths[customers_model.name].path)

    _logger.info("Transform completed successfully")
