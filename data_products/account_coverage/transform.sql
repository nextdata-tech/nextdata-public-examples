-- Reset the target so a partial run can't leave stale rows alongside fresh ones.
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].account_coverage }};

INSERT INTO {{ outputs["snowflake"].account_coverage }}
WITH activity_agg AS (
    SELECT
        account_id,
        COUNT(activity_id)                                                       AS touch_count,
        SUM(estimated_cost_usd)                                                  AS total_cost_usd,
        COALESCE(ROUND(AVG(engagement_score), 2), 0)                             AS avg_engagement_score,
        SUM(CASE WHEN response = 'Positive' THEN 1 ELSE 0 END)                   AS pos_count,
        SUM(CASE WHEN response IN ('Negative', 'No Response') THEN 1 ELSE 0 END) AS neg_no_resp,
        SUM(CASE WHEN channel = 'F2F' THEN 1 ELSE 0 END)                        AS f2f_count
    FROM {{ inputs.data_products["crm-activity"].snowflake.activity }}
    GROUP BY account_id
)
SELECT
    a.account_id,
    a.account_value_tier,
    a.segment,
    a.specialty,
    a.territory_id,
    a.potential_value_usd,
    a.actual_value_usd,
    a.potential_value_usd - a.actual_value_usd                            AS value_gap_usd,
    realization_ratio(a.actual_value_usd, a.potential_value_usd)          AS realization_ratio,
    COALESCE(ag.touch_count, 0)                                            AS touch_count,
    COALESCE(ag.total_cost_usd, 0)                                         AS total_cost_usd,
    COALESCE(ag.avg_engagement_score, 0)                                   AS avg_engagement_score,
    positive_rate(COALESCE(ag.pos_count, 0), COALESCE(ag.touch_count, 0)) AS positive_rate,
    coverage_flag(
        a.account_value_tier,
        a.potential_value_usd,
        a.actual_value_usd,
        COALESCE(ag.touch_count, 0),
        COALESCE(ag.pos_count, 0),
        COALESCE(ag.neg_no_resp, 0),
        COALESCE(ag.f2f_count, 0)
    )                                                                      AS coverage_flag
FROM {{ inputs.data_products["crm-activity"].snowflake.account }} a
LEFT JOIN activity_agg ag ON a.account_id = ag.account_id;
