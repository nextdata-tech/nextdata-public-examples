USE SCHEMA REP_TERRITORY_PERFORMANCE;
CREATE OR REPLACE TEMPORARY PROCEDURE COMPUTE_REP_TERRITORY_SCORECARD(
    activity_table STRING,
    target_table STRING
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
IMPORTS = ('@rep_territory_performance/scorecard.py')
HANDLER = 'scorecard.build_scorecard'
AS
$$
$$;

-- Reset the target so a partial run can't leave stale rows alongside fresh ones.
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].rep_territory_scorecard }};

CALL COMPUTE_REP_TERRITORY_SCORECARD(
    '{{ inputs.data_products["crm-activity"].snowflake.activity }}',
    '{{ outputs["snowflake"].rep_territory_scorecard }}'
);
