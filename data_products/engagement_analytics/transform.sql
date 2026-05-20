-- 1. CHANNEL_EFFECTIVENESS — engagement & cost-efficiency by channel
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].channel_effectiveness }};

INSERT INTO {{ outputs["snowflake"].channel_effectiveness }}
    (channel, activity_count, avg_engagement_score, positive_rate,
     on_preferred_channel_rate, total_cost_usd, cost_per_positive_usd)
SELECT
    channel,
    COUNT(*) AS activity_count,
    ROUND(AVG(engagement_score), 2) AS avg_engagement_score,
    ROUND(SUM(CASE WHEN response = 'Positive' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS positive_rate,
    ROUND(SUM(CASE WHEN on_preferred_channel THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS on_preferred_channel_rate,
    SUM(estimated_cost_usd) AS total_cost_usd,
    COALESCE(ROUND(SUM(estimated_cost_usd)
             / NULLIF(SUM(CASE WHEN response = 'Positive' THEN 1 ELSE 0 END), 0), 2), 0) AS cost_per_positive_usd
FROM {{ inputs.data_products["crm-activity"].snowflake.activity }}
GROUP BY channel;

-- 2. MONTHLY_TRENDS — monthly engagement & F2F-to-digital shift
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].monthly_trends }};

INSERT INTO {{ outputs["snowflake"].monthly_trends }}
    (activity_month, activity_count, avg_engagement_score, positive_rate,
     f2f_share, digital_share, total_cost_usd)
SELECT
    activity_month,
    COUNT(*) AS activity_count,
    ROUND(AVG(engagement_score), 2) AS avg_engagement_score,
    ROUND(SUM(CASE WHEN response = 'Positive' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS positive_rate,
    ROUND(SUM(CASE WHEN channel = 'F2F' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS f2f_share,
    ROUND(SUM(CASE WHEN channel IN ('Email', 'Remote', 'Virtual Event') THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 4) AS digital_share,
    SUM(estimated_cost_usd) AS total_cost_usd
FROM {{ inputs.data_products["crm-activity"].snowflake.activity }}
GROUP BY activity_month
ORDER BY activity_month;

-- 3. REP_TERRITORY_SCORECARD — rep/territory perf incl. field vs HQ
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].rep_territory_scorecard }};

INSERT INTO {{ outputs["snowflake"].rep_territory_scorecard }}
    (rep_id, territory_id, is_hq_campaign, activity_count, distinct_accounts,
     avg_engagement_score, positive_rate, total_cost_usd, avg_cost_per_activity_usd)
SELECT
    rep_id,
    territory_id,
    (rep_id ILIKE 'MKTG%' OR territory_id = 'T-MKT') AS is_hq_campaign,
    COUNT(*) AS activity_count,
    COUNT(DISTINCT account_id) AS distinct_accounts,
    ROUND(AVG(engagement_score), 2) AS avg_engagement_score,
    ROUND(SUM(CASE WHEN response = 'Positive' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS positive_rate,
    SUM(estimated_cost_usd) AS total_cost_usd,
    ROUND(AVG(estimated_cost_usd), 2) AS avg_cost_per_activity_usd
FROM {{ inputs.data_products["crm-activity"].snowflake.activity }}
GROUP BY rep_id, territory_id;
