# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="product-competitiveness",
        domain="FINANCE/COMPETITORS/PRODUCTS",
        description="Current term deposit and home loan rates from competitor analysis",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/product_competitiveness",
    )
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
    )
    .environment("demo")
    .input(
        "market-rates",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/market-rates#/output/port/adls")
        .environment("demo")
        .with_file_type(SupportedFormat.JSON)
        .expectation(westpac_home_loans)
        .expectation(
            custom("westpac-home-loan-portfolios")
            .verify(code(adls_atleast_one_record.verify))
            .description("Expect 3 different LVR codes in Westpac home loans")
        ),
    )
    .output(
        data_product_output()
        .promise(term_deposits)
        .promise(home_loan_rates)
        # TODO: Currently, this doesn't really work without removing .verify_field() calls in the models
        .promise(
            custom("snowflake_atleast_one_record_contract")
            .verify(code(snowflake_atleast_one_record.verify))
            .service(service_name="nxd-snowflake", driver="nxd:snowflake:1.0.0")
        )
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config("PRODUCT_COMPETITIVENESS")
                .target_table("TERM_DEPOSITS", term_deposits)
                .target_table("HOME_LOAN_RATES", home_loan_rates)
            ),
        )
    )
    .output(
        data_product_rpc_output()
        .function(rpc_function(code(get_banks), get_banks_request, get_banks_response).description("get_banks"))
        .function(
            rpc_function(
                code(get_term_deposit_rates),
                get_term_deposit_rates_request,
                get_term_deposit_rates_response,
            ).description("get_term_deposit_rates")
        )
        .function(
            rpc_function(
                code(get_home_loan_rates),
                get_home_loan_rates_request,
                get_home_loan_rates_response,
            ).description("get_term_deposit_rates")
        )
        .port(
            "mcp-api",
            rpc_server("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/mcp-api-service-k8s")
            .enable_endpoints()
            .mcp_path("/mcp"),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
