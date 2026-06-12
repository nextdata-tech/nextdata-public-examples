# ruff: noqa: F403, F405
from nxd_spec import *

# Single shared infra profile (matches and the MCP examples).
# The Snowflake service backs both the transform and the output storage port; the
# k8s MCP service backs the rpc port that exposes the three tools.
SNOWFLAKE_SERVICE = (
    "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake"
)
MCP_API_SERVICE = (
    "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/mcp-api-service-k8s"
)

spec = (
    data_product(
        name="account-coverage",
        description=(
            "Per-account coverage and value-gap analysis over the crm-activity feed: "
            "realized vs. potential value, touch volume, cost, engagement, and an "
            "opinionated coverage classification flagging under-served high-value and "
            "over-served low-value accounts. The transform runs as SQL on Snowflake "
            "compute; the coverage logic and the natural-language account profile both "
            "live in a Snowpark Python stored procedure declared and CALLed from "
            "transform.sql. Exposes three MCP tools: get_schema (table metadata read "
            "from models.py), execute_query (agent-authored SQL via the Snowflake MCP "
            "server), and search_accounts (Cortex Search semantic similarity over "
            "account profiles)."
        ),
        domain="COMMERCIAL/ANALYTICS",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
    )
    .environment("demo")
    # Snowflake-compute transform: computes the coverage table (incl. the profile
    # text Cortex Search indexes) from the crm-activity inputs.
    .transform(
        sql("transform.sql").compute(SNOWFLAKE_SERVICE)
    )
    # Input: the upstream crm-activity product (account + activity tables).
    .input(
        "crm_activity",
        data_product_input()
        .source("https://app.demo.trynxd.com/data-product/crm-activity#/output/port/snowflake")
        .expectation(account)
        .expectation(activity),
    )
    # Output 1: the Snowflake table holding the computed coverage rows.
    .output(
        data_product_output()
        .promise(account_coverage)
        .port(
            "snowflake",
            storage(SNOWFLAKE_SERVICE).config(
                snowflake_config("ACCOUNT_COVERAGE").target_table(
                    "ACCOUNT_COVERAGE", account_coverage
                )
            ),
        )
    )
    # Output 2: the MCP endpoint exposing the three tools.
    .output(
        data_product_rpc_output()
        .function(
            rpc_function(
                code(get_schema),
                get_schema_request,
                get_schema_response,
            ).description(
                "Return the account-coverage table's columns, types, and rich descriptions "
                "read live from the semantic model in models.py, plus guidance on choosing "
                "between execute_query (SQL) and search_accounts (Cortex Search). Call first."
            )
        )
        .function(
            rpc_function(
                code(execute_query),
                execute_query_request,
                execute_query_response,
            ).description(
                "Execute a single read-only SELECT or WITH statement that the agent authored "
                "against PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE. For structured "
                "filters, aggregations, and rankings. Call get_schema first."
            )
        )
        .function(
            rpc_function(
                code(search_accounts),
                search_accounts_request,
                search_accounts_response,
            ).description(
                "Natural-language semantic search over account profiles via the "
                "ACCOUNT_COVERAGE_SEARCH Cortex Search service. For fuzzy, descriptive "
                "'find accounts like ...' questions. Pass plain English, not SQL."
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
