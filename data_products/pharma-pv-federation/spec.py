# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="pharma-pv-federation",
        domain="pharmacovigilance/analytics",
        description=(
            "Federated pharmacovigilance analytics orchestrator. "
            "Joins two governed domains — Drug Safety (adverse-event counts, the numerator) "
            "and Commercial Analytics (prescription volume, the denominator) — to compute "
            "the adverse-event reporting rate per 1,000 prescriptions: the key PV signal "
            "metric that neither domain can produce alone. "
            "Exposes two MCP tools: get_metadata (live schema + join keys) and "
            "execute_federated_query (runs the cross-domain JOIN in Snowflake). "
            "All underlying data is SYNTHETIC; products are FICTIONAL."
        ),
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
    )
    .environment("demo")
    .transform(
        sql("transform/build_pv_registry.sql")
        .compute("https://nextopia.dev/infra-profile/ecommerce-demo#/services/nxd-snowflake")
        .when(
            any_of(
                updated("drug-safety-signals"),
                updated("commercial-prescriptions"),
                scheduled("0 0 * * *"),
            ),
            startup=True,
        )
    )
    .input(
        "drug-safety-signals",
        data_product_input().source(
            "https://nextopia.dev/data-product/drug-safety-signals#/output/port/snowflake"
        ),
    )
    .input(
        "commercial-prescriptions",
        data_product_input().source(
            "https://nextopia.dev/data-product/commercial-prescriptions#/output/port/snowflake"
        ),
    )
    .output(
        data_product_output()
        .model(pv_registry)
        .port(
            "snowflake",
            storage("https://nextopia.dev/infra-profile/ecommerce-demo#/services/nxd-snowflake")
            .config(
                snowflake_config(schema="pharma_pv_federation")
                .target_table("pv_registry", pv_registry)
            )
            .model(pv_registry)
            .promise(pv_registry),
        )
    )
    .output(
        data_product_rpc_output()
        .function(
            rpc_function(
                code(get_metadata),
                get_metadata_request,
                get_metadata_response,
            ).description(
                "Live schema metadata for the two federated PV tables: "
                "adverse_event_summary (Drug Safety — AE numerator) and "
                "prescription_volume (Commercial — Rx denominator). "
                "Returns real column names from INFORMATION_SCHEMA, join keys "
                "(product_id, region, report_period), and the key federated metric formula "
                "(reporting rate per 1,000 Rx). Call FIRST before execute_federated_query."
            )
        )
        .function(
            rpc_function(
                code(execute_federated_query),
                execute_federated_query_request,
                execute_federated_query_response,
            ).description(
                "Execute a SQL SELECT (cross-domain pharmacovigilance JOIN) in Snowflake. "
                "Joins adverse_event_summary (Drug Safety) with prescription_volume "
                "(Commercial) on product_id, region, report_period to compute the "
                "adverse-event reporting rate per 1,000 prescriptions. "
                "Use fully-qualified names: PARTNER_AZ_DB.drug_safety_signals.adverse_event_summary. "
                "Call get_metadata first. Only SELECT or WITH allowed."
            )
        )
        .port(
            "mcp-api",
            rpc_server(
                "https://app.demo.trynxd.com/infra-profile/ecommerce-demo-api#/services/mcp-api-service-k8s"
            )
            .enable_endpoints()
            .mcp_path("/mcp"),
        )
    )
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
