CREATE OR REPLACE TEMPORARY PROCEDURE COMPUTE_REP_TERRITORY_SCORECARD(
    activity_table STRING,
    target_table STRING
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
IMPORTS = ('@rep_territory_performance/scorecard.py')
HANDLER = 'run'
AS
$$
import sys, os, gzip

# PUT commands are auto compressing files even with AUTO_COMPRESS = FALSE, thus we read and execute manually
def run(session, activity_table, target_table):
    import_dir = sys._xoptions["snowflake_import_directory"]
    with gzip.open(os.path.join(import_dir, "scorecard.py"), "rt") as f:
        src = f.read()
    ns = {}
    exec(src, ns)
    return ns["build_scorecard"](session, activity_table, target_table)
$$;

-- Reset the target so a partial run can't leave stale rows alongside fresh ones.
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].rep_territory_scorecard }};

CALL COMPUTE_REP_TERRITORY_SCORECARD(
    '{{ inputs.data_products["crm-activity"].snowflake.activity }}',
    '{{ outputs["snowflake"].rep_territory_scorecard }}'
);
