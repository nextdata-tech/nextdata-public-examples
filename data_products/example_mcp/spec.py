# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="example-mcp-server",
        domain="tutorial",
        description="Example MCP server exposing bank data through a Model Context Protocol endpoint, enabling AI agents to query structured financial data via natural language.",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/example_mcp",
    )
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks")
        .config(cluster_config)
    )
    .environment("demo")
    .output(
        data_product_output()
        .promise(banks)
        .promise(
            custom("databricks-atleast-one-record")
            .verify(
                code(databricks_atleast_one_record.verify)
                .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks-contract")
                .config(cluster_config)
            )
            .model(banks)
            .description("Verifies each promised Databricks table contains at least one record")
        )
        .port(
            "nxd-databricks-storage",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks-storage").config(
                databricks_config().target_table("BANK", banks)
            ),
        )
    )
    .output(
        data_product_rpc_output()
        .function(rpc_function(code(get_banks), get_banks_request, get_banks_response).description("get_banks"))
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
