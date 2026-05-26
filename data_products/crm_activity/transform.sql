-- Load the seed data uploaded to the user stage during provisioning
-- (see provision.sql, which PUTs account.csv / activity.csv into @~/crm_activity/).

TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].account }};

COPY INTO {{ outputs["snowflake"].account }}
    (account_id, account_type, first_name, last_name, hco_name, npi, specialty, city, state, prescribing_decile, segment, account_value_tier, potential_value_usd, actual_value_usd, preferred_channel, email_opt_in, target_flag, territory_id, primary_rep_id, status)
FROM @~/crm_activity/account.csv
FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"' EMPTY_FIELD_AS_NULL = TRUE NULL_IF = ('', 'NULL'))
ON_ERROR = ABORT_STATEMENT;

TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].activity }};

COPY INTO {{ outputs["snowflake"].activity }}
    (activity_id, account_id, rep_id, territory_id, activity_datetime, activity_month, channel, activity_type, product_discussed, detail_priority, duration_min, engagement_score, response, on_preferred_channel, sample_dropped, sample_quantity, estimated_cost_usd, next_best_action, follow_up_required)
FROM @~/crm_activity/activity.csv
FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"' EMPTY_FIELD_AS_NULL = TRUE NULL_IF = ('', 'NULL'))
ON_ERROR = ABORT_STATEMENT;
