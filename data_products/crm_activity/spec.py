# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="crm-activity",
        description=(
            "CRM field-sales engagement data for the pharmaceutical commercial team. "
            "Combines a curated set of accounts (healthcare professionals and "
            "organizations with their specialty, value tiering, and territory "
            "assignment) with the field activities logged against them (calls, "
            "details, sample drops, follow-ups, and inquiries), capturing channel, "
            "product discussed, engagement outcome, cost, and next best action."
        ),
        domain="COMMERCIAL",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/crm_activity",
    )
    .environment("demo")
    .provision(sql("provision.sql"))
    .transform(
        sql("transform.sql")
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake")
        .when(scheduled("0 */12 * * *"), startup=True)
    )
    .output(
        data_product_output()
        .promise(account)
        .promise(activity)
        .promise(custom("email_opt_in_missing").verify(code(email_opt_in_missing)))
        .promise(custom("orphan_activity").verify(code(orphan_activity)))
        .promise(custom("invalid_npi").verify(code(invalid_npi)))
        .promise(custom("inconsistent_casing").verify(code(inconsistent_casing)))
        .promise(custom("inactive_account_with_activity").verify(code(inactive_account_with_activity)))
        # Register the semantic views (consume-time only — never promised /
        # produced) so their metric annotations reach the kernel's manifest and
        # the .semantic_tools() payload.
        .model(account_metrics)
        .model(activity_metrics)
        .port(
            "snowflake",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-snowflake").config(
                snowflake_config(schema="CRM_ACTIVITY")
                .target_table("ACCOUNT", account)
                .target_table("ACTIVITY", activity)
            ),
        )
    )
    # Auto-wire the four governed semantic MCP tools (list_models,
    # describe_model, semantic_model, run_semantic_query) from the field-level
    # annotations on the models above, served over the demo mesh MCP api service.
    .semantic_tools(service="mcp-api-service-k8s")
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("owner", owner().user("hello@nextdata.com"))
)
