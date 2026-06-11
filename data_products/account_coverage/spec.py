# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="account-coverage",
        description=(
            "Per-account coverage and value-gap analysis over the crm-activity "
            "feed: realized vs. potential value, touch volume, cost, engagement, "
            "and an opinionated coverage classification flagging under-served "
            "high-value and over-served low-value accounts. The transform runs "
            "as SQL on Snowflake compute; the coverage logic itself lives in a "
            "Snowpark Python stored procedure declared and CALLed from "
            "transform.sql. Exposes three MCP tools: get_schema (table metadata), "
            "execute_query (SQL execution via Snowflake MCP Server), and "
            "search_accounts (Cortex Search semantic similarity over account profiles)."
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
    # -- ETL output -- Snowflake table -----------------------------------------
    .output(
        data_product_output()
        .promise(account_coverage)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config("ACCOUNT_COVERAGE").target_table("ACCOUNT_COVERAGE", account_coverage)
            ),
        )
    )
    # -- MCP output -- three tools exposed via the Nextdata proxy --------------
    .output(
        data_product_rpc_output()
        # Tool 1: get_schema -- metadata, no DB access
        .function(
            rpc_function(
                code(get_schema),
                get_schema_request,
                get_schema_response,
            ).description(
                "Returns the complete ACCOUNT_COVERAGE table schema including "
                "column names, data types, allowed values, and example SQL. "
                "Call before execute_query."
            )
        )
        # Tool 2: execute_query -- precise SQL via Snowflake MCP Server
        .function(
            rpc_function(
                code(execute_query),
                execute_query_request,
                execute_query_response,
            ).description(
                "Executes a SQL SELECT query against PARTNER_AZ_DB.ACCOUNT_COVERAGE.ACCOUNT_COVERAGE "
                "via the Snowflake MCP Server sql_exec_tool. "
                "Use for precise structured queries with known column values."
            )
        )
        # Tool 3: search_accounts -- semantic search via Cortex Search
        .function(
            rpc_function(
                code(search_accounts),
                search_accounts_request,
                search_accounts_response,
            ).description(
                "Searches accounts by natural language description using Snowflake Cortex Search. "
                "Finds accounts by semantic similarity over account_profile_text. "
                "Use for exploratory questions -- complement to execute_query, not a replacement."
            )
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
