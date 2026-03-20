# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="example-mcp-server",
        domain="tutorial",
        description="Example MCP server",
        version="0.0.1-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-examples",
    )
    .transform(
        code(transform)
        .compute(
            "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute"
        )
        .config(k8s_executor_config)
    )
    .environment("demo")
    .output(
        data_product_output()
        .promise(banks)
        .port(
            "snowflake",
            storage(
                "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake"
            ).config(snowflake_config("EXAMPLE_MCP").target_table("BANK", banks)),
        )
    )
    .output(
        data_product_rpc_output()
        .function(
            rpc_function(
                code(get_banks), get_banks_request, get_banks_response
            ).description("get_banks")
        )
        .port(
            "mcp-api",
            rpc_server(
                "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/mcp-api-service-k8s"
            )
            .enable_endpoints()
            .mcp_path("/mcp"),
        )
    )
)
