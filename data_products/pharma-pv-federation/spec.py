# ruff: noqa: F403, F405
from nxd_spec import *

# Single shared infra profile (matches account-coverage and the MCP examples).
# The Snowflake service backs both the transform and the output storage port;
# the k8s MCP service backs the rpc port that exposes the two tools.
SNOWFLAKE_SERVICE = (
    "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake"
)
MCP_API_SERVICE = (
    "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/mcp-api-service-k8s"
)

spec = (
    data_product(
        name="pharma-pv-federation",
        description=(
            "Pharmacovigilance federation orchestrator. Exposes two MCP tools "
            "(get_metadata, execute_federated_query) that let an AI agent run "
            "arbitrary read-only, cross-domain SQL joining adverse-event data "
            "(drug-safety-signals) with prescription volumes (commercial-"
            "prescriptions) in Snowflake to compute adverse-event reporting "
            "rates per 1,000 prescriptions. The agent fetches the live schema "
            "first and then authors its own SQL, so it is never limited to a "
            "fixed list of questions."
        ),
        domain="LIFE-SCIENCES/PHARMACOVIGILANCE",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
    )
    .environment("demo")
    # Snowflake-compute transform that writes the single constant anchor row.
    .transform(
        sql("transform/build_pv_registry.sql").compute(SNOWFLAKE_SERVICE)
    )
    # Output 1: the Snowflake table that anchors this product's live credentials.
    .output(
        data_product_output()
        .promise(pv_registry)
        .port(
            "snowflake",
            storage(SNOWFLAKE_SERVICE).config(
                snowflake_config("PHARMA_PV_FEDERATION").target_table(
                    "PV_REGISTRY", pv_registry
                )
            ),
        )
    )
    # Output 2: the MCP endpoint exposing the two federation tools.
    .output(
        data_product_rpc_output()
        .function(
            rpc_function(
                code(get_metadata),
                get_metadata_request,
                get_metadata_response,
            ).description(
                "Return the live schema (column names, types, and comments) of "
                "the two federated pharmacovigilance tables, plus the join keys "
                "(product_id, region, report_period) and the adverse-event-per-"
                "1,000-Rx rate metric. ALWAYS call this first."
            )
        )
        .function(
            rpc_function(
                code(execute_federated_query),
                execute_federated_query_request,
                execute_federated_query_response,
            ).description(
                "Execute a single read-only SELECT or WITH statement in "
                "Snowflake -- typically the cross-domain JOIN of "
                "adverse_event_summary with prescription_volume that computes "
                "the adverse-event reporting rate per 1,000 prescriptions. Call "
                "get_metadata first; use fully-qualified table names."
            )
        )
        .port(
            "mcp-api",
            rpc_server(MCP_API_SERVICE).enable_endpoints().mcp_path("/mcp"),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
