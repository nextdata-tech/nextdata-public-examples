-- Build the Cortex registry: one constant anchor row.
--
-- We use CREATE OR REPLACE TABLE ... AS SELECT (not INSERT) on purpose. This
-- transform owns the table definition outright, so the physical table is
-- always rebuilt to exactly match the columns produced here. That makes the
-- deploy self-healing: it cannot fail with an "invalid identifier" error when
-- an older version of this data product left a CORTEX_REGISTRY table behind
-- with a different set of columns. It also reads NO other schema and counts
-- NO upstream rows, so it can never panic on an empty or not-yet-visible
-- source table.
--
-- The table is only an anchor: it gives this data product a concrete Snowflake
-- output so the platform issues live Snowflake credentials, which the ask MCP
-- tool then borrows to call the Snowflake MCP server that wraps the Cortex
-- Agent. Nothing downstream consumes CORTEX_REGISTRY, so replacing it is safe.
--
-- Plain ASCII only. Do not introduce en-dash or em-dash characters anywhere in
-- this file (including comments): the Snowflake SQL parser panics on them.

CREATE OR REPLACE TABLE {{ outputs["snowflake"].cortex_registry }} AS
SELECT
    'engagement-cortex'                                                              AS registry_id,
    'PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_CORTEX_MCP_SRVR'                     AS mcp_server,
    'PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_ANALYST_AGENT'                       AS agent,
    '@PARTNER_AZ_DB.ENGAGEMENT_CORTEX.SEMANTIC_MODELS/engagement_analytics.yaml'     AS semantic_model_file,
    'PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.CHANNEL_EFFECTIVENESS'                       AS channel_table,
    'PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.MONTHLY_TRENDS'                              AS monthly_table,
    CURRENT_TIMESTAMP()::STRING                                                       AS built_at;
