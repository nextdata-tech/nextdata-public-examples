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
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/westpac_term_deposits/attributes/product_id",
    )
    .link(
        "name",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/macquarie_term_deposits/attributes/title",
    )
    .link(
        "min_amount",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/macquarie_term_deposits/attributes/title",
    )
    .link(
        "max_amount",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/macquarie_term_deposits/attributes/title",
    )
    .link(
        "min_term",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/westpac_term_deposits/attributes/min_term",
    )
    .link(
        "max_term",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/westpac_term_deposits/attributes/max_term",
    )
    .link(
        "monthly_rate",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/westpac_term_deposits/attributes/monthly_rate",
    )
    .link(
        "monthly_rate",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/macquarie_term_deposits/attributes/value",
    )
    .link(
        "annual_rate",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/westpac_term_deposits/attributes/maturity_rate",
    )
    .link(
        "annual_rate",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/macquarie_term_deposits/attributes/value",
    )
    .link(
        "maturity_rate",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/westpac_term_deposits/attributes/maturity_rate",
    )
    .link(
        "maturity_rate",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/macquarie_term_deposits/attributes/value",
    )
    # .verify_field("bank", match_regex(r"Westpac|ANZ|Macquarie"))
)

home_loan_rates = (
    semantic_model("home_loan_rates")
    .sampling(SamplingMethod.Random)
    .description("Conformed home loan rates across banks in America")
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
        "product",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/westpac_home_loans/attributes/portfolioid",
    )
    .link(
        "product",
        Predicate.Derived,
        "https://nextopia.dev/data-product/demo/market-rates#/models/anz_products/attributes/name",
    )
    # .verify_field("bank", match_regex(r"Westpac|ANZ|Macquarie"))
)


def _field(name: str | None, data_type: DataType) -> Field:
    # helper function for DataType.ComplexType which expects
    #   Field classes and not dicts or tuples
    return Field(
        data_type=data_type,
        name=name,
        description=None,
        metadata=None,
        constraints=None,
        relates_to=[],
        semantic_tags=None,
    )


westpac_home_loans = semantic_model(
    name="westpac_home_loans",
    description="Westpac Home Loan Rates. Captured from a web request that feeds Westpac's home loan calculator (https://www.westpac.com.au/personal-banking/home-loans/calculator/mortgage-repayment/)",
    attributes=[
        attribute(
            name="PortfolioId",
            data_type=string(),
            description="Home Loan LVR product code",
        ),
        attribute(
            name="Products",
            data_type=list(
                _field(
                    "item",
                    struct([_field("1 Year Fixed Rate Investment Property Loan", string())]),
                )
            ),
            description="List of home loan products rates at different LVR levels",
        ),
    ],
)
