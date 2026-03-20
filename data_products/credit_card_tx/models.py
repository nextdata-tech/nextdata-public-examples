# ruff: noqa: F403, F405
from nxd_models import *

customers = (
    semantic_model(
        name="customers",
        description="Represents individuals who hold credit card accounts and perform transactions.",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "customer_id": (
                string(),
                "Unique identifier for the customer across all systems.",
            ),
            "email": (
                string(),
                "Redacted email address associated with the customer for communication and verification.",
            ),
        }
    )
)

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
