# ruff: noqa: F403, F405
from nxd_models import *

# region Output

anomalies = (
    semantic_model(
        name="anomalies",
        description="Contains credit card transactions identified as suspicious due to occurring in different countries within the same hour for the same customer.",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "transaction_id": (
                string(),
                "Unique identifier assigned to each credit card transaction flagged as anomalous.",
            ),
            "customer_id": (
                string(),
                "Identifier linking the transaction to the corresponding customer, used to track multiple suspicious transactions for the same customer.",
            ),
            "date": (
                timestamp(unit=DurationUnit.Nanoseconds),
                "Timestamp when the transaction occurred, recorded with nanosecond precision.",
            ),
            "country_code": (
                string(),
                "ISO country code representing the country where the suspicious transaction took place.",
            ),
        }
    )
    .link(
        "transaction_id",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/credit-card-tx#/models/transactions/attributes/transaction_id",
    )
    .link(
        "customer_id",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/credit-card-tx#/models/transactions/attributes/customer_id",
    )
    .link(
        "date",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/credit-card-tx#/models/transactions/attributes/date",
    )
    .link(
        "country_code",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/credit-card-tx#/models/transactions/attributes/country_code",
    )
)

# endregion Output

# region Input

transactions = (
    semantic_model(
        name="transactions",
        description="Captures all credit card transaction records including purchase details, amounts, and merchant information.",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "transaction_id": (
                string(),
                "Unique identifier assigned to each credit card transaction.",
            ),
            "customer_id": (
                string(),
                "Identifier linking the transaction to the corresponding customer.",
            ),
            "date": (
                timestamp(unit=DurationUnit.Nanoseconds),
                "Timestamp when the transaction occurred, recorded in nanosecond precision.",
            ),
            "type": (
                string(),
                "Type of transaction (e.g., purchase, refund, cash withdrawal, payment).",
            ),
            "amount": (
                int64(),
                "Monetary value of the transaction in the smallest currency unit (e.g., cents).",
            ),
            "merchant": (
                string(),
                "Name or identifier of the merchant where the transaction was made.",
            ),
            "country_code": (
                string(),
                "ISO country code representing the country where the transaction took place.",
            ),
        }
    )
)

# endregion Input
