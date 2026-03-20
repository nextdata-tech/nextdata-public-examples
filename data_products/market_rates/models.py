# ruff: noqa: F403, F405
from nxd_models import *


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


anz_products = (
    semantic_model(
        name="anz_products",
        description="ANZ Product Data. Captured from an ASP.NET request on ANZ's calculator webpage (https://www.anz.com.au/personal/bank-accounts/term-deposits/advance-notice/)",
    )
    .sampling(method=SamplingMethod.Random)
    .schema(
        {
            "code": (string(), "Product category code"),
            "name": (string(), "Product category name"),
            "isactive": (string(), "Is active product"),
            "isfordisplay": (string(), "Is displayed on the website"),
            "sectiondescription": (string(), "Product category description"),
            "sectioneffectivedate": (
                string(),
                "Date on which the product category became effective. (Friday, 22 August 2025)",
            ),
            "sectioneffectivedateraw": (
                string(),
                "Timestamp on which the product category became effective. (22/08/2025 6:50:37 AM)",
            ),
            "informationurl": (string(), "URL to product category on website"),
            "sectiondisclaimer": (string(), "Product category disclaimer"),
            "subsection": (
                list(
                    _field(
                        "item",
                        struct(
                            [
                                _field("code", string()),
                                _field("name", string()),
                                _field("isactive", string()),
                                _field("isfordisplay", string()),
                                _field("name", string()),
                                _field("tiergrouptitle1", string()),
                                _field("tiergrouptitle2", string()),
                                _field("subsectiondescription", string()),
                                _field("subsectiondisclaimer", string()),
                                _field(
                                    "baserate",
                                    list(
                                        _field(
                                            "item",
                                            struct(
                                                [
                                                    _field("code", string()),
                                                    _field("name", string()),
                                                    _field("isactive", string()),
                                                    _field(
                                                        "isfordisplay",
                                                        string(),
                                                    ),
                                                    _field("ratename", string()),
                                                    _field("ratetype", string()),
                                                    _field("ratevalue", string()),
                                                    _field(
                                                        "ratesuffix",
                                                        string(),
                                                    ),
                                                    _field("ratenote", string()),
                                                    _field("tiername1", string()),
                                                    _field("tiername2", string()),
                                                ]
                                            ),
                                        )
                                    ),
                                ),
                            ]
                        ),
                    )
                )
            ),
        }
    )
)

westpac_term_deposits = semantic_model(
    name="westpac_term_deposits",
    description="Westpac Term Deposit Rates. Captured from a web request that feeds Westpac's term deposit calculator (https://www.westpac.com.au/personal-banking/bank-accounts/term-deposit/rate-calculator/)",
    attributes=[
        attribute(
            name="product_id",
            data_type=string(),
            description="Product ID (TermDeposit-10000~0.25)",
        ),
        attribute(
            name="status",
            data_type=string(),
            description="Product status on website (PUBLISHED)",
        ),
        attribute(
            name="rate_code", data_type=string(), description="Rate code (10000~0.25)"
        ),
        attribute(
            name="product",
            data_type=string(),
            description="Name of the product (Term Deposit - 10000~0.25)",
        ),
        attribute(
            name="min_amount",
            data_type=string(),
            description="Minimum deposit amount required",
        ),
        attribute(
            name="min_term",
            data_type=string(),
            description="Minimum term required for this product",
        ),
        attribute(
            name="max_term",
            data_type=string(),
            description="Maximum term required for this product",
        ),
        attribute(
            name="max_amount", data_type=string(), description="Maximum deposit amount"
        ),
        attribute(
            name="maturity_rate",
            data_type=string(),
            description="Interest received at maturity (% per annum)",
        ),
        attribute(
            name="monthly_rate",
            data_type=string(),
            description="Monthly interest received (% per annum)",
        ),
        attribute(
            name="hot_rate",
            data_type=string(),
            description="Special offer rates (% per annum)",
        ),
        attribute(
            name="effective_date",
            data_type=string(),
            description="Date on which this product began to be offered (18/07/2025)",
        ),
    ],
).sampling(method=SamplingMethod.Random)

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
                    struct(
                        [_field("1 Year Fixed Rate Investment Property Loan", string())]
                    ),
                )
            ),
            description="List of home loan products rates at different LVR levels",
        ),
    ],
).sampling(method=SamplingMethod.Random)

macquarie_term_deposits = semantic_model(
    name="macquarie_term_deposits",
    description="Macquarie Term Deposit Rates. Captured from a web request used to display rates on Macquarie's website. (https://www.macquarie.com.au/everyday-banking/term-deposits.html)",
    attributes=[
        attribute(
            name="title",
            data_type=string(),
            description="Name of the product (term_deposit_macquarie_bank_monthly_3_months_1m)",
        ),
        attribute(
            name="value",
            data_type=string(),
            description="Term deposit rate (% per annum)",
        ),
    ],
).sampling(method=SamplingMethod.Random)

macquarie_home_loans = semantic_model(
    name="macquarie_home_loans",
    description="Macquarie Home Loan Rates. Captured from a web request used to display rates on Macquarie's website. (https://www.macquarie.com.au/home-loans/home-loan-rates.html)",
    attributes=[
        attribute(
            name="title",
            data_type=string(),
            description="Name of the product (mort_basic_fix_5year_tier1_lte90_inv_rate)",
        ),
        attribute(
            name="value",
            data_type=string(),
            description="Term deposit rate (% per annum)",
        ),
    ],
).sampling(method=SamplingMethod.Random)
