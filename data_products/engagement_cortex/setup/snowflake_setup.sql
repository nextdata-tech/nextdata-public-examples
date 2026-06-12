USE DATABASE PARTNER_AZ_DB;

-- Schema lives in PARTNER_AZ_DB alongside ENGAGEMENT_ANALYTICS, ACCOUNT_COVERAGE,
-- etc. Comment included so it surfaces in INFORMATION_SCHEMA / Snowsight.
CREATE SCHEMA IF NOT EXISTS PARTNER_AZ_DB.ENGAGEMENT_CORTEX
    COMMENT = 'Engagement Cortex: Snowflake MCP server + Cortex Agent + Cortex Analyst stack that the engagement-cortex NXD data product bridges to.';

USE SCHEMA PARTNER_AZ_DB.ENGAGEMENT_CORTEX;

-- Internal stage that hosts the Cortex Analyst YAML semantic model. The agent
-- references the file via @PARTNER_AZ_DB.ENGAGEMENT_CORTEX.SEMANTIC_MODELS/<file>.
-- SSE encryption is the Snowflake default for internal stages, which Cortex
-- Analyst requires when reading semantic_model_file from a stage.
CREATE STAGE IF NOT EXISTS SEMANTIC_MODELS
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Cortex Analyst YAML semantic models for engagement-cortex.';

-- Confirm.
SHOW STAGES IN SCHEMA PARTNER_AZ_DB.ENGAGEMENT_CORTEX;

-- ------------------------------------------------------------------------------
-- upload the semantic model yaml file
-- ------------------------------------------------------------------------------


CREATE OR REPLACE AGENT PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_ANALYST_AGENT
    WITH PROFILE = '{"display_name": "Engagement Analytics Cortex Agent"}'
    COMMENT = 'Cortex Agent that answers natural-language questions about engagement-analytics by routing them to Cortex Analyst (text-to-SQL + execute) using the engagement_analytics.yaml semantic model.'
    FROM SPECIFICATION $$
models:
  orchestration: auto

instructions:
  response: |
    Provide a concise, business-language answer. Lead with the headline
    finding (a number, a ranking, or a comparison), then briefly explain
    what was measured. Do not paste raw SQL into the prose answer; the
    caller already receives it as structured output.
  orchestration: |
    Always use the Analyst_Tool for engagement questions about channels,
    monthly trends, or the F2F-to-digital shift. The Analyst_Tool both
    authors AND executes the SQL on the configured warehouse, so a single
    tool call is enough -- do not retry on success and do not split a
    question into multiple analyst calls when one will do.
  system: |
    You are an analytics assistant over pharmaceutical commercial CRM
    engagement data. The data covers channel-level effectiveness
    (engagement quality, positive-response rate, on-preferred-channel rate,
    cost per positive) and month-level trends (volume, engagement quality,
    F2F-to-digital channel mix shift). Always report rates and shares as
    percentages with one decimal. Always report currency in whole USD.

tools:
  - tool_spec:
      type: "cortex_analyst_text_to_sql"
      name: "Analyst_Tool"
      description: |
        Translates natural-language questions about engagement analytics into
        SQL using the engagement_analytics.yaml semantic model, runs the SQL
        on the configured warehouse, and returns the rows.

tool_resources:
  Analyst_Tool:
    semantic_model_file: "@PARTNER_AZ_DB.ENGAGEMENT_CORTEX.SEMANTIC_MODELS/engagement_analytics.yaml"
    execution_environment:
      type: warehouse
      warehouse: PARTNER_AZ_WH
      query_timeout: 60
$$;

SHOW AGENTS IN SCHEMA PARTNER_AZ_DB.ENGAGEMENT_CORTEX;
DESC AGENT PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_ANALYST_AGENT;

-- Smoke-test the agent directly via DATA_AGENT_RUN (bypasses the MCP layer).
-- If this returns a reasonable JSON response, the agent + Analyst + warehouse
-- are healthy and the next step (CREATE MCP SERVER) only adds the MCP envelope.
SELECT TRY_PARSE_JSON(
    SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
        'PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_ANALYST_AGENT',
        $${"messages":[{"role":"user","content":[{"type":"text","text":"Which channel has the highest positive response rate?"}]}]}$$
    )
) AS agent_smoke_test;


-- --------------------------------------------------------------------------------------------------------------------


CREATE OR REPLACE MCP SERVER PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_CORTEX_MCP_SRVR
    COMMENT = 'Snowflake-managed MCP server wrapping ENGAGEMENT_ANALYST_AGENT. Exposes one tool (ask_engagement) of type CORTEX_AGENT_RUN. The engagement-cortex NXD data product calls this server.'
    FROM SPECIFICATION $$
tools:
  - title:       "Ask Engagement Agent"
    name:        "ask_engagement"
    type:        "CORTEX_AGENT_RUN"
    identifier:  "PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_ANALYST_AGENT"
    description: |
      Ask a natural-language question about pharmaceutical commercial CRM
      engagement analytics: per-channel effectiveness and cost-efficiency,
      monthly trends, and the F2F-to-digital channel mix shift. The wrapped
      Cortex Agent runs Cortex Analyst over the engagement_analytics.yaml
      semantic model, which both authors AND executes the SQL on the
      configured warehouse. Forward the user's question verbatim.
$$;

-- Sanity check.
SHOW MCP SERVERS IN SCHEMA PARTNER_AZ_DB.ENGAGEMENT_CORTEX;
DESC MCP SERVER PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_CORTEX_MCP_SRVR;

-- -------------------------------------------------------------------------------------------------
-- permissions
-- -------------------------------------------------------------------------------------------------

GRANT USAGE ON MCP SERVER PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_CORTEX_MCP_SRVR TO ROLE PARTNER_AZ_ROLE;


-- Source tables Cortex Analyst will SELECT from when it runs the generated SQL
GRANT USAGE  ON SCHEMA PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS
  TO ROLE PARTNER_AZ_ROLE;
GRANT SELECT ON TABLE  PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.CHANNEL_EFFECTIVENESS
  TO ROLE PARTNER_AZ_ROLE;
GRANT SELECT ON TABLE  PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.MONTHLY_TRENDS
  TO ROLE PARTNER_AZ_ROLE;

-- 1. Schema + stage access.
GRANT USAGE ON DATABASE PARTNER_AZ_DB                          TO ROLE PARTNER_AZ_ROLE;
GRANT USAGE ON SCHEMA   PARTNER_AZ_DB.ENGAGEMENT_CORTEX        TO ROLE PARTNER_AZ_ROLE;
GRANT READ  ON STAGE    PARTNER_AZ_DB.ENGAGEMENT_CORTEX.SEMANTIC_MODELS TO ROLE PARTNER_AZ_ROLE;

-- 2. Cortex Agent + MCP server use.
GRANT USAGE ON AGENT      PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_ANALYST_AGENT   TO ROLE  PARTNER_AZ_ROLE;
GRANT USAGE ON MCP SERVER PARTNER_AZ_DB.ENGAGEMENT_CORTEX.ENGAGEMENT_CORTEX_MCP_SRVR TO ROLE  PARTNER_AZ_ROLE;

-- 3. Read the engagement-analytics tables that Cortex Analyst will query.
--    The agent runs SQL in the role of whoever calls DATA_AGENT_RUN / the MCP
--    server, which (through the NXD data product chain) is the DP role. So
--    that role needs SELECT on the upstream tables.
GRANT USAGE  ON SCHEMA PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS                              TO ROLE PARTNER_AZ_ROLE;
GRANT SELECT ON TABLE  PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.CHANNEL_EFFECTIVENESS        TO ROLE PARTNER_AZ_ROLE;
GRANT SELECT ON TABLE  PARTNER_AZ_DB.ENGAGEMENT_ANALYTICS.MONTHLY_TRENDS               TO ROLE PARTNER_AZ_ROLE;

-- 4. Warehouse Cortex Analyst will execute SQL on (matches
--    execution_environment.warehouse in 03_create_agent.sql).
GRANT USAGE, OPERATE ON WAREHOUSE PARTNER_AZ_WH                             TO ROLE PARTNER_AZ_ROLE;

-- 5. Sanity: list what the DP role can see in our schema.
USE ROLE PARTNER_AZ_ROLE;
SHOW GRANTS ON SCHEMA PARTNER_AZ_DB.ENGAGEMENT_CORTEX;

GRANT USAGE, CREATE TABLE ON SCHEMA PARTNER_AZ_DB.ENGAGEMENT_CORTEX
  TO ROLE PARTNER_AZ_ROLE;


-----------------------------------------------------------------------------

