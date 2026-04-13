# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="competitor-growth-analysis",
        description="Structured and unstructured competitor analysis",
        domain="FINANCE/COMPETITORS/FINANCIAL-PERFORMANCE",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-examples",
    )
    .environment("demo")
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks")
        .config(cluster_config)
        .when(
            any_of(
                updated("market-announcements"),
                updated("income-statements"),
                updated("stock-history"),
                updated("financial-statements"),
                updated("company-dividends"),
            )
        )
    )
    .input(
        "market-announcements",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/market-announcements#/output/port/adls")
        .environment("demo"),
        # .expectation(announcements),
    )
    .input(
        "income-statements",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/income-statements#/output/port/adls")
        .environment("demo"),
        # .expectation(income_statements),
    )
    .input(
        "stock-history",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/stock-history#/output/port/adls")
        .environment("demo"),
        # .expectation(history),
    )
    .input(
        "financial-statements",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/financial-statements#/output/port/adls")
        .environment("demo"),
    )
    .input(
        "company-dividends",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/company-dividends#/output/port/adls")
        .environment("demo"),
    )
    .input(
        "aps-330-public-disclosures",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/public-disclosures#/output/port/adls")
        .environment("demo"),
    )
    .output(
        data_product_output()
        .model(documents)
        .model(growth)
        .model(dividend_sustainability)
        .port(
            "adls",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/adls")
            .config(
                adls_config()
                .target_file("documents/**/*.json", documents)
                .target_file("growth.parquet", growth)
                .target_file("dividend_sustainability.parquet", dividend_sustainability)
            )
            .promise(growth)
            .promise(dividend_sustainability)
            .disable_temporal_credentials()
            .follow_approval_flow()
            .approval(
                access_approval_config(
                    "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/servicenow-sp-approval"
                )
            ),
        )
        .port(
            "nxd-databricks-storage",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks-storage")
            .config(databricks_config())
            .promise(growth)
            .promise(dividend_sustainability),
        )
    )
    .output(
        data_product_rpc_output()
        .function(
            rpc_function(
                code(get_bank_symbols),
                get_bank_symbols_request,
                get_bank_symbols_response,
            ).description("Retrieve available bank symbols with growth and shareholder returns data for analysis")
        )
        .function(
            rpc_function(
                code(get_growth),
                get_growth_request,
                get_growth_response,
            ).description(
                "Retrieve financial growth and shareholder returns for a given bank for given symbols. Check available symbols with get_bank_symbols tool"
            )
        )
        .function(
            rpc_function(
                code(get_dividend_sustainability),
                get_dividend_sustainability_request,
                get_dividend_sustainability_response,
            ).description("Retrieve Year-over-year dividend sustainability analysis banks Bank of America, Citigroup")
        )
        .port(
            "mcp-api",
            rpc_server("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/mcp-api-service-k8s")
            .enable_endpoints()
            .mcp_path("/mcp"),
        )
    )
    .control("owner", owner().user("hello@nextdata.com"))
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
)
