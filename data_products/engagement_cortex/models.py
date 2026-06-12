# ruff: noqa: F403, F405
"""
models.py -- semantic model for the engagement-cortex data product.

This data product is an MCP-to-MCP bridge. It owns no engagement-analytics
data: that lives in the upstream engagement-analytics product
(PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.{CHANNEL_EFFECTIVENESS, MONTHLY_TRENDS}).

The single anchor table CORTEX_REGISTRY exists only so the platform issues
this product live Snowflake credentials. The single MCP tool (ask) borrows
those credentials to invoke a Snowflake MCP server that wraps a Cortex Agent;
the Cortex Agent uses Cortex Analyst to generate AND execute the SQL against
the engagement tables and returns the answer in one call. No SQL execution
happens in this Python pod -- that's the whole point of the new architecture.

The transform that fills CORTEX_REGISTRY reads NO other schema and counts NO
upstream rows, so it cannot fail because a source table is empty or not yet
visible. It is pure metadata.
"""

from nxd_models import *

cortex_registry = semantic_model(
    name="cortex_registry",
    description=(
        "Cortex Agent + Analyst registry. A single anchor row describing the "
        "Snowflake MCP server, Cortex Agent, and Cortex Analyst semantic model "
        "that the ask tool routes natural-language questions through. Carries "
        "no PII and no engagement-level data."
    ),
).schema(
    {
        "registry_id": (
            string(),
            "Constant identifier for this Cortex registry ('engagement-cortex').",
        ),
        "mcp_server": (
            string(),
            "Fully-qualified name of the Snowflake MCP server the ask tool calls "
            "(PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_CORTEX_MCP_SRVR).",
        ),
        "agent": (
            string(),
            "Fully-qualified name of the Cortex Agent the MCP server wraps "
            "(PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_ANALYST_AGENT).",
        ),
        "semantic_model_file": (
            string(),
            "Stage path of the Cortex Analyst YAML semantic model the agent "
            "uses for text-to-SQL "
            "(@PARTNER_AZ_DB.ENGAGEMENT_CORTEX.SEMANTIC_MODELS/engagement_analytics.yaml).",
        ),
        "channel_table": (
            string(),
            "Fully-qualified channel-effectiveness table the semantic model maps "
            "to (PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.CHANNEL_EFFECTIVENESS).",
        ),
        "monthly_table": (
            string(),
            "Fully-qualified monthly-trend table the semantic model maps to "
            "(PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.MONTHLY_TRENDS).",
        ),
        "built_at": (
            string(),
            "UTC timestamp text recording when this registry row was last rebuilt.",
        ),
    }
)
