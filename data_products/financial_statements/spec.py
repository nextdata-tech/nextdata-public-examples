# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="financial-statements",
        description="Financial Statement metrics for publicly listed companies",
        domain="FINANCE/COMPETITORS/FINANCIAL-PERFORMANCE",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/financial_statements",
    )
    .environment("demo")
    .transform(
        script("transform.py")
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks")
        .when(any_of(scheduled("0 */8 * * *"), on_started()))
    )
    .input(
        "competitor-data-api",
        source_aligned_input()
        .source("https://nextopia.dev/infra-profile/ecommerce-demo#/services/sec-comp-summary-api")
        .model(source_documents)
        .expectation(source_documents)
        .expectation(custom("check_document_format").verify(code(check_document_format))),
    )
    .output(
        data_product_output()
        .port(
            "adls",
            storage("https://nextopia.dev/infra-profile/ecommerce-demo#/services/adls")
            .config(
                adls_config(
                    file_type=SupportedFormat.PARQUET,
                )
            )
            .managed_access()
            .promise(custom("pii_rag").verify(code(check_pii)))
            .promise(custom("check_freshness").verify(code(check_freshness))),
        )
        .port(
            "databricks",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks-storage").config(
                databricks_config()
            ),
        )
        .promise(cash_flows)
        .promise(balance_sheets)
        .promise(source_documents)
    )
    .output(
        data_product_rpc_output()
        .function(
            rpc_function(
                code(get_revenue),
                RevenueAPI.get_request_model(),
                RevenueAPI.get_response_model(),
            ).description("Retrieve revenue data for a given company.")
        )
        .function(
            rpc_function(
                code(get_top_revenue),
                TopRevenueAPI.get_request_model(),
                TopRevenueAPI.get_response_model(),
            ).description("Retrieve top revenue companies for a given year.")
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
