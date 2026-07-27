# ruff: noqa: F403, F405
from nxd_spec import *

_coverage_flag_udf = udf.python(
    name="coverage_flag",
    args=[
        ("account_value_tier", "VARCHAR"),
        ("potential_value_usd", "FLOAT"),
        ("actual_value_usd", "FLOAT"),
        ("touch_count", "NUMBER"),
        ("pos_count", "NUMBER"),
        ("neg_no_resp", "NUMBER"),
        ("f2f_count", "NUMBER"),
    ],
    returns="VARCHAR",
    runtime_version="3.10",
    source=udf.from_callable(_coverage_flag_fn),
    handler="coverage_flag",
    comment="Classifies account coverage tier from activity and value metrics",
)

_realization_ratio_udf = udf.python(
    name="realization_ratio",
    args=[("actual_value_usd", "FLOAT"), ("potential_value_usd", "FLOAT")],
    returns="FLOAT",
    runtime_version="3.10",
    source=udf.from_callable(_realization_ratio_fn),
    handler="realization_ratio",
    comment="Actual / potential value, guarded against zero denominator, rounded to 4dp",
)

_positive_rate_udf = udf.python(
    name="positive_rate",
    args=[("pos_count", "NUMBER"), ("touch_count", "NUMBER")],
    returns="FLOAT",
    runtime_version="3.10",
    source=udf.from_callable(_positive_rate_fn),
    handler="positive_rate",
    comment="Fraction of touches with Positive response, guarded against zero denominator",
)


spec = (
    data_product(
        name="account-coverage",
        description=(
            "Per-account coverage and value-gap analysis over the crm-activity "
            "feed: realized vs. potential value, touch volume, cost, engagement, "
            "and an opinionated coverage classification flagging under-served "
            "high-value and over-served low-value accounts. The transform runs "
            "as plain SQL on Snowflake compute; the coverage logic lives in three "
            "Python scalar UDFs (coverage_flag, realization_ratio, positive_rate) "
            "registered via the output port."
        ),
        domain="COMMERCIAL/ANALYTICS",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/account_coverage",
    )
    .environment("demo")
    .transform(
        sql("transform.sql").compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake")
    )
    .input(
        "crm_activity",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/crm-activity#/output/port/snowflake")
        .expectation(account)
        .expectation(activity),
    )
    .output(
        data_product_output()
        .promise(account_coverage)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config(schema="ACCOUNT_COVERAGE")
                .target_table("ACCOUNT_COVERAGE", account_coverage)
                .with_udf(_coverage_flag_udf)
                .with_udf(_realization_ratio_udf)
                .with_udf(_positive_rate_udf)
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
