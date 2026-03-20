# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="loans-products",
        domain="FINANCE/COMPETITORS/PRODUCTS",
        description="Competitor analysis of home loan product pricing, including rates and terms and conditions",
        version="0.0.1-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-examples",
    )
    .environment("demo")
    .with_global_trigger(ScheduleTrigger("0 */8 * * *"))
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
    )
    .input(
        "product-competitiveness",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/product-competitiveness#/output/port/snowflake")
        .environment("demo")
        .expectation(
            custom("expect-data-from-all-banks")
            .verify(code(expect_data_from_all_banks.verify))
            .description("Check each model to ensure data is available for Bank of America, Citigroup")
        ),
    )
    .output(
        data_product_output()
        .promise(term_deposits)
        .promise(home_loan_rates)
        .promise(
            custom("snowflake_atleast_one_record_contract")
            .verify(code(snowflake_atleast_one_record.verify))
            .service(service_name="nxd-snowflake", driver="nxd:snowflake:1.0.0")
            .model(term_deposits)
            .model(home_loan_rates)
        )
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config("CUSTOMER_RATES")
                .target_table("TERM_DEPOSITS", term_deposits)
                .target_table("HOME_LOAN_RATES", home_loan_rates)
            ),
        )
    )
    .control("owner", owner().user("hello@nextdata.com"))
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
)
