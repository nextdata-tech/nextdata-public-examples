-- 1. ACCOUNT_COVERAGE — value-gap & coverage classification
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].account_coverage }};

INSERT INTO {{ outputs["snowflake"].account_coverage }}
    (account_id, account_value_tier, segment, specialty, territory_id,
     potential_value_usd, actual_value_usd, value_gap_usd, realization_ratio,
     touch_count, total_cost_usd, avg_engagement_score, positive_rate, coverage_flag)
SELECT
    a.account_id,
    a.account_value_tier,
    a.segment,
    a.specialty,
    a.territory_id,
    a.potential_value_usd,
    a.actual_value_usd,
    a.potential_value_usd - a.actual_value_usd AS value_gap_usd,
    CASE WHEN a.potential_value_usd > 0
         THEN ROUND(a.actual_value_usd / a.potential_value_usd, 4) ELSE 0 END AS realization_ratio,
    COUNT(act.activity_id) AS touch_count,
    COALESCE(SUM(act.estimated_cost_usd), 0) AS total_cost_usd,
    COALESCE(ROUND(AVG(act.engagement_score), 2), 0) AS avg_engagement_score,
    COALESCE(ROUND(SUM(CASE WHEN act.response = 'Positive' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(act.activity_id), 0), 4), 0) AS positive_rate,
    CASE
        WHEN UPPER(a.account_value_tier) = 'HIGH'
             AND (a.actual_value_usd / NULLIF(a.potential_value_usd, 0)) < 0.25
             AND COUNT(act.activity_id) <= 2
            THEN 'Under-served high-value'
        WHEN UPPER(a.account_value_tier) = 'HIGH'
             AND COUNT(act.activity_id) >= 3
             AND SUM(CASE WHEN act.response = 'Positive' THEN 1 ELSE 0 END) = COUNT(act.activity_id)
            THEN 'Well-served high-value'
        WHEN UPPER(a.account_value_tier) = 'LOW'
             AND SUM(CASE WHEN act.channel = 'F2F' THEN 1 ELSE 0 END) >= 1
             AND SUM(CASE WHEN act.response IN ('Negative', 'No Response') THEN 1 ELSE 0 END) >= 1
            THEN 'Over-served low-value'
        ELSE 'Adequate'
    END AS coverage_flag
FROM {{ inputs.data_products["crm-activity"].snowflake.account }} a
LEFT JOIN {{ inputs.data_products["crm-activity"].snowflake.activity }} act
    ON act.account_id = a.account_id
GROUP BY a.account_id, a.account_value_tier, a.segment, a.specialty, a.territory_id,
         a.potential_value_usd, a.actual_value_usd;

-- 2. CHANNEL_EFFECTIVENESS — engagement & cost-efficiency by channel
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

-- 3. MONTHLY_TRENDS — monthly engagement & F2F-to-digital shift
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

-- 4. REP_TERRITORY_SCORECARD — rep/territory perf incl. field vs HQ
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

-- 5. DATA_QUALITY_FINDINGS — referential-integrity & dirt report
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].data_quality_findings }};

INSERT INTO {{ outputs["snowflake"].data_quality_findings }}
    (finding_type, entity_type, entity_id, detail)
SELECT 'orphan_activity', 'activity', act.activity_id,
       'activity references unknown account_id ' || act.account_id
FROM {{ inputs.data_products["crm-activity"].snowflake.activity }} act
LEFT JOIN {{ inputs.data_products["crm-activity"].snowflake.account }} a ON a.account_id = act.account_id
WHERE a.account_id IS NULL
UNION ALL
SELECT 'invalid_npi', 'account', account_id,
       'npi ' || COALESCE(TO_VARCHAR(npi), '<null>') || ' is not a 10-digit identifier'
FROM {{ inputs.data_products["crm-activity"].snowflake.account }}
WHERE npi IS NULL OR LENGTH(TO_VARCHAR(npi)) <> 10
UNION ALL
SELECT 'inconsistent_casing', 'account', account_id,
       'non-canonical casing in first_name / last_name / status'
FROM {{ inputs.data_products["crm-activity"].snowflake.account }}
WHERE (first_name IS NOT NULL AND first_name <> INITCAP(first_name))
   OR (last_name IS NOT NULL AND last_name <> INITCAP(last_name))
   OR (status IS NOT NULL AND status <> INITCAP(status))
UNION ALL
SELECT 'missing_email_opt_in', 'account', account_id,
       'email_opt_in is null'
FROM {{ inputs.data_products["crm-activity"].snowflake.account }}
WHERE email_opt_in IS NULL
UNION ALL
SELECT 'inactive_account_with_activity', 'account', a.account_id,
       'account status is Inactive but has ' || COUNT(act.activity_id) || ' activities'
FROM {{ inputs.data_products["crm-activity"].snowflake.account }} a
JOIN {{ inputs.data_products["crm-activity"].snowflake.activity }} act ON act.account_id = a.account_id
WHERE UPPER(a.status) = 'INACTIVE'
GROUP BY a.account_id;
