from nxd.spec import data_product

spec = (
    data_product(
        name="fraud-analytics-glossary",
        description=(
            "Business glossary for the Fraud Analytics domain. "
            "Defines canonical terms for fraud density metrics and "
            "merchant market categories used across all fraud detection "
            "data products."
        ),
        domain="FINANCE/FRAUD-DETECTION",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
    )
    .environment("demo")
    .glossary("glossary.yaml")
)
