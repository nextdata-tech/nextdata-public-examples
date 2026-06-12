-- transform.sql -- account-coverage
--
-- Computes one row per account from the crm-activity inputs (account + activity)
-- and writes them to the NXD-managed ACCOUNT_COVERAGE table, including the
-- natural-language account_profile_text that the ACCOUNT_COVERAGE_SEARCH Cortex
-- Search service indexes for the search_accounts tool.
--
-- This is PURE, FULLY-QUALIFIED SQL on purpose. An earlier version computed the
-- rows in a Snowpark stored procedure, but the transform session has no current
-- schema, so an unqualified CREATE TEMPORARY PROCEDURE failed with
--   "Cannot perform CREATE TEMPPROCEDURE. This session does not have a current
--    schema. Call 'USE SCHEMA', or use a qualified name."
-- Every object here is referenced by its fully-qualified name (via the Jinja
-- input/output placeholders), so nothing depends on a current schema being set.
--
-- The target is TRUNCATEd (not dropped) and appended to, so the NXD-managed
-- table object -- and therefore the Cortex Search service that references it --
-- is preserved across runs and simply re-indexes the fresh rows.
--
-- ASCII only: non-ASCII punctuation (em dashes, smart quotes) crashes the
-- Snowflake SQL parser.

-- Reset the target so a partial run can't leave stale rows alongside fresh ones.
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].account_coverage }};

-- Recompute every account's coverage row and load it.
INSERT INTO {{ outputs["snowflake"].account_coverage }}
    (account_id, account_value_tier, segment, specialty, territory_id,
     potential_value_usd, actual_value_usd, value_gap_usd, realization_ratio,
     touch_count, total_cost_usd, avg_engagement_score, positive_rate,
     coverage_flag, account_profile_text)
SELECT
    base.account_id,
    base.account_value_tier,
    base.segment,
    base.specialty,
    base.territory_id,
    base.potential_value_usd,
    base.actual_value_usd,
    base.value_gap_usd,
    base.realization_ratio,
    base.touch_count,
    base.total_cost_usd,
    base.avg_engagement_score,
    base.positive_rate,
    base.coverage_flag,
    'Account ' || base.account_id
        || ' is a ' || COALESCE(base.account_value_tier, 'Unknown') || '-value '
        || COALESCE(base.specialty, 'Unknown specialty')
        || ' practice in sales territory ' || COALESCE(base.territory_id, '?')
        || ', field-force segment ' || COALESCE(base.segment, '?') || '. '
        || 'Coverage classification: ' || base.coverage_flag || '. '
        || 'Potential value $' || base.potential_value_usd::STRING
        || ', realized value $' || base.actual_value_usd::STRING
        || ', unrealized value gap $' || base.value_gap_usd::STRING
        || ' (' || base.realization_pct::STRING || ' percent realized). '
        || 'Logged ' || base.touch_count::STRING || ' field activities at total cost $'
        || base.total_cost_usd::STRING
        || ', average engagement score ' || base.avg_engagement_score::STRING
        || ' out of 100, positive response rate ' || base.positive_pct::STRING
        || ' percent.'                                              AS account_profile_text
FROM (
    SELECT
        a.account_id,
        a.account_value_tier,
        a.segment,
        a.specialty,
        a.territory_id,
        a.potential_value_usd,
        a.actual_value_usd,
        a.potential_value_usd - a.actual_value_usd                  AS value_gap_usd,
        CASE WHEN a.potential_value_usd > 0
             THEN ROUND(a.actual_value_usd / a.potential_value_usd, 4)
             ELSE 0 END                                            AS realization_ratio,
        COALESCE(ag.touch_count, 0)                                AS touch_count,
        COALESCE(ag.total_cost_usd, 0)                             AS total_cost_usd,
        COALESCE(ROUND(ag.avg_engagement_raw, 2), 0)               AS avg_engagement_score,
        CASE WHEN COALESCE(ag.touch_count, 0) > 0
             THEN ROUND(COALESCE(ag.positive_count, 0) / ag.touch_count, 4)
             ELSE 0 END                                            AS positive_rate,
        CASE
            WHEN UPPER(a.account_value_tier) = 'HIGH'
                 AND a.potential_value_usd > 0
                 AND (a.actual_value_usd / a.potential_value_usd) < 0.25
                 AND COALESCE(ag.touch_count, 0) <= 2
                THEN 'Under-served high-value'
            WHEN UPPER(a.account_value_tier) = 'HIGH'
                 AND COALESCE(ag.touch_count, 0) >= 3
                 AND COALESCE(ag.positive_count, 0) = COALESCE(ag.touch_count, 0)
                THEN 'Well-served high-value'
            WHEN UPPER(a.account_value_tier) = 'LOW'
                 AND COALESCE(ag.f2f_count, 0) >= 1
                 AND COALESCE(ag.neg_no_resp, 0) >= 1
                THEN 'Over-served low-value'
            ELSE 'Adequate'
        END                                                        AS coverage_flag,
        -- helper percentages used only to render account_profile_text
        CASE WHEN a.potential_value_usd > 0
             THEN ROUND(a.actual_value_usd / a.potential_value_usd * 100, 1)
             ELSE 0 END                                            AS realization_pct,
        CASE WHEN COALESCE(ag.touch_count, 0) > 0
             THEN ROUND(COALESCE(ag.positive_count, 0) / ag.touch_count * 100, 1)
             ELSE 0 END                                            AS positive_pct
    FROM {{ inputs.data_products["crm-activity"].snowflake.account }} a
    LEFT JOIN (
        SELECT
            account_id,
            COUNT(activity_id)                                              AS touch_count,
            SUM(estimated_cost_usd)                                         AS total_cost_usd,
            AVG(engagement_score)                                           AS avg_engagement_raw,
            SUM(CASE WHEN response = 'Positive' THEN 1 ELSE 0 END)          AS positive_count,
            SUM(CASE WHEN response IN ('Negative', 'No Response') THEN 1 ELSE 0 END) AS neg_no_resp,
            SUM(CASE WHEN channel = 'F2F' THEN 1 ELSE 0 END)               AS f2f_count
        FROM {{ inputs.data_products["crm-activity"].snowflake.activity }}
        GROUP BY account_id
    ) ag
      ON a.account_id = ag.account_id
) base;