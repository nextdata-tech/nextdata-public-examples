# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="market-rates",
        domain="FINANCE/COMPETITORS/MARKET-INTELLIGENCE",
        description="Data collected as part of competitor analysis from publicly available websites",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/market_rates",
    )
    .input(
        "comp_public",
        source_aligned_input()
        .source("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/yahoo-finance")
        .model(anz_products)
        .expectation(anz_products)
        .expectation(
            custom("api-atleast-one-record")
            .verify(code(api_atleast_one_record.verify))
            .description("Verifies the ANZ API source returns at least one record")
        ),
    )
    .input(
        "nextopia_public",
        source_aligned_input()
        .source("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/yahoo-finance")
        .model(westpac_home_loans)
        .expectation(westpac_home_loans)
        .expectation(
            custom("api-atleast-one-record")
            .verify(code(api_atleast_one_record.verify))
            .description("Verifies the Westpac API source returns at least one record")
        ),
    )
    .input(
        "comp2_public",
        source_aligned_input()
        .source("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/yahoo-finance")
        .model(macquarie_home_loans)
        .expectation(macquarie_home_loans)
        .expectation(
            custom("api-atleast-one-record")
            .verify(code(api_atleast_one_record.verify))
            .description("Verifies the Macquarie API source returns at least one record")
        ),
    )
    .environment("demo")
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
    )
    .with_global_trigger(ScheduleTrigger("0 */8 * * *"))
    .output(
        data_product_output()
        .promise(anz_products)
        .promise(westpac_term_deposits)
        .promise(macquarie_term_deposits)
        .promise(westpac_home_loans)
        .promise(macquarie_home_loans)
        .port(
            "adls",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/adls")
            .config(adls_config(file_type=SupportedFormat.JSON))
            .managed_access()
            .promise(
                custom("adls-non-empty-output")
                .verify(code(adls_freshness.verify))
                .description("Verifies each promised output model in ADLS contains at least one record")
            ),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
