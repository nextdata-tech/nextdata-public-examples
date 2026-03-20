# ruff: noqa: F403, F405
from nxd_models import *

term_deposits = (
    semantic_model("term_deposits")
    .sampling(SamplingMethod.Random)
    .description("Term Deposit data conformed and aggregated across banks")
    .schema(
        {
            "name": (string(), "Name of the product"),
            "bank": (string(), "Name of the bank (Bank of America, Citigroup)"),
            "min_amount": (int64(), "Minimum deposit to be eligible for this product"),
            "max_amount": (int64(), "Maximum deposit to be eligible for this product"),
            "min_term": (int64(), "Minimum term in months"),
            "max_term": (int64(), "Maximum term in months"),
            "monthly_rate": (decimal(4, 2), "Interest paid out monthly in % per annum"),
            "annual_rate": (decimal(4, 2), "Interest paid out annually in % per annum"),
            "maturity_rate": (
                decimal(4, 2),
                "Interest paid out at maturity in % per annum",
            ),
        }
    )
    .link(
        "name",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/term_deposits/attributes/name",
    )
    .link(
        "bank",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/term_deposits/attributes/bank",
    )
    .link(
        "min_amount",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/term_deposits/attributes/min_amount",
    )
    .link(
        "max_amount",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/term_deposits/attributes/max_amount",
    )
    .link(
        "min_term",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/term_deposits/attributes/min_term",
    )
    .link(
        "max_term",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/term_deposits/attributes/max_term",
    )
    .link(
        "monthly_rate",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/term_deposits/attributes/monthly_rate",
    )
    .link(
        "annual_rate",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/term_deposits/attributes/annual_rate",
    )
    .link(
        "maturity_rate",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/term_deposits/attributes/maturity_rate",
    )
)


home_loan_rates = (
    semantic_model("home_loan_rates")
    .sampling(SamplingMethod.Random)
    .description("Conformed home loan rates across banks in US")
    .schema(
        {
            "bank": (string(), "Name of the bank (Bank of America, Citigroup)"),
            "product": (string(), "Name of the product"),
            "loan_term": (int64(), "Length of the loan in years"),
            "min_lvr": (int64(), "Minimum LVR to be eligible for this product"),
            "max_lvr": (int64(), "Maximum LVR to be eligible for this product"),
            "min_loan": (int64(), "Minimum loan to be eligible for this product"),
            "max_loan": (int64(), "Maximum loan to be eligible for this product"),
            "rate": (decimal(6, 2), "Interest rate (% per annum)"),
        }
    )
    .link(
        "bank",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/home_loan_rates/attributes/bank",
    )
    .link(
        "product",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/home_loan_rates/attributes/product",
    )
    .link(
        "loan_term",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/home_loan_rates/attributes/loan_term",
    )
    .link(
        "min_lvr",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/home_loan_rates/attributes/min_lvr",
    )
    .link(
        "max_lvr",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/home_loan_rates/attributes/max_lvr",
    )
    .link(
        "min_loan",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/home_loan_rates/attributes/min_loan",
    )
    .link(
        "max_loan",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/home_loan_rates/attributes/max_loan",
    )
    .link(
        "rate",
        Predicate.SameAs,
        "https://nextopia.dev/data-product/demo/product-competitiveness#/models/home_loan_rates/attributes/rate",
    )
)
