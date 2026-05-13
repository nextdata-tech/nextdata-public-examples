from nxd.spec import data_product

spec = (
    data_product(
        name="retail-catalog-glossary",
        description=(
            "Business glossary for the Retail Catalog domain. "
            "Defines canonical terms for product pricing, categorisation, "
            "and brand attributes used across retail catalog data products."
        ),
        domain="RETAIL/CATALOG/PRICING",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
    )
    .environment("demo")
    .glossary("glossary.yaml")
)
