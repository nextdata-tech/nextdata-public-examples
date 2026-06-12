# ruff: noqa: F403, F405
from nxd_spec import *

# Single shared infra profile (matches account-coverage and pharma-pv-federation).
# The Snowflake service backs both the transform and the output storage port;
# the k8s MCP service backs the rpc port that exposes the single ask tool.
SNOWFLAKE_SERVICE = (
    "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake"
)
MCP_API_SERVICE = (
    "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/mcp-api-service-k8s"
)

spec = (
    data_product(
        name="engagement-cortex",
        description=(
            "Natural-language interface to engagement-analytics via Snowflake "
            "Cortex Agent + Analyst, bridged from Claude Desktop through an NXD "
            "RPC pod. Exposes ONE MCP tool (ask) that forwards the user's "
            "question verbatim to a Snowflake MCP server "
            "(ENGAGEMENT_CORTEX_MCP_SRVR), whose CORTEX_AGENT_RUN tool invokes "
            "ENGAGEMENT_ANALYST_AGENT. The agent's Cortex Analyst tool both "
            "authors and executes the SQL against PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS "
            "(CHANNEL_EFFECTIVENESS, MONTHLY_TRENDS) using the YAML semantic model "
            "in @PARTNER_AZ_DB.ENGAGEMENT_CORTEX.SEMANTIC_MODELS/engagement_analytics.yaml. "
            "Claude Desktop never sees a schema, never fetches metadata, and "
            "never writes SQL -- it just asks questions."
        ),
        domain="COMMERCIAL/ANALYTICS",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
    )
    .environment("demo")
    # Snowflake-compute transform that writes the single constant anchor row.
    # This anchor exists ONLY so the platform issues live Snowflake credentials
    # to the RPC pod; the ask tool borrows those credentials to call the
    # Snowflake MCP server.
    .transform(
        sql("transform/build_cortex_registry.sql").compute(SNOWFLAKE_SERVICE)
    )
    # Output 1: the Snowflake table that anchors this product's live credentials.
    .output(
        data_product_output()
        .promise(cortex_registry)
        .port(
            "snowflake",
            storage(SNOWFLAKE_SERVICE).config(
                snowflake_config("ENGAGEMENT_CORTEX").target_table(
                    "CORTEX_REGISTRY", cortex_registry
                )
            ),
        )
    )
    # Output 2: the MCP endpoint exposing the single ask tool.
    .output(
        data_product_rpc_output()
        .function(
            rpc_function(
                code(ask),
                ask_request,
                ask_response,
            ).description(
                "Ask a natural-language question about engagement analytics. "
                "Forward the user's question verbatim in the 'question' "
                "argument -- do NOT author SQL and do NOT fetch any schema "
                "first. Returns 'answer' (business-language summary), 'sql' "
                "(the SQL Cortex Analyst authored and already executed), "
                "'data' (the executed result as a tab-separated text table), "
                "and 'row_count'. This is the ONLY tool on the product; one "
                "call per question."
            )
        )
        .port(
            "mcp-api",
            rpc_server(MCP_API_SERVICE).enable_endpoints().mcp_path("/mcp"),
        )
    )
    .control("data-product-access", data_product_access().user("tushar.sharma.datacolor@nextdata.com"))
    .control("steward", data_product_access().user("tushar.sharma.datacolor@nextdata.com"))
    .control("owner", owner().user("tushar.sharma.datacolor@nextdata.com"))
)
