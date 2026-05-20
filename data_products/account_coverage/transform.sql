CREATE OR REPLACE TEMPORARY PROCEDURE COMPUTE_ACCOUNT_COVERAGE(
    account_table STRING,
    activity_table STRING,
    target_table STRING
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
AS
$$
from snowflake.snowpark.functions import (
    avg, coalesce, col, count, lit, round as round_, sum as sum_, upper, when,
)


def main(session, account_table: str, activity_table: str, target_table: str) -> str:
    account = session.table(account_table)
    activity = session.table(activity_table)

    # Per-account activity rollup. Rename account_id so the post-join schema
    # doesn't end up with two ACCOUNT_ID columns to disambiguate.
    activity_agg = (
        activity.group_by("account_id")
        .agg(
            count("activity_id").alias("touch_count_raw"),
            sum_("estimated_cost_usd").alias("total_cost_raw"),
            avg("engagement_score").alias("avg_engagement_raw"),
            sum_(when(col("response") == lit("Positive"), lit(1)).otherwise(lit(0))).alias("positive_count"),
            sum_(
                when(col("response").isin(lit("Negative"), lit("No Response")), lit(1)).otherwise(lit(0))
            ).alias("neg_no_resp_count"),
            sum_(when(col("channel") == lit("F2F"), lit(1)).otherwise(lit(0))).alias("f2f_count"),
        )
        .with_column_renamed("account_id", "agg_account_id")
    )

    joined = account.join(
        activity_agg,
        account["account_id"] == activity_agg["agg_account_id"],
        "left",
    )

    touch_count = coalesce(col("touch_count_raw"), lit(0))
    total_cost = coalesce(col("total_cost_raw"), lit(0))
    pos_count = coalesce(col("positive_count"), lit(0))
    neg_no_resp = coalesce(col("neg_no_resp_count"), lit(0))
    f2f_count = coalesce(col("f2f_count"), lit(0))

    realization_ratio = when(
        col("potential_value_usd") > lit(0),
        round_(col("actual_value_usd") / col("potential_value_usd"), lit(4)),
    ).otherwise(lit(0))

    avg_engagement = coalesce(round_(col("avg_engagement_raw"), lit(2)), lit(0))
    positive_rate = when(
        touch_count > lit(0),
        round_(pos_count / touch_count, lit(4)),
    ).otherwise(lit(0))

    coverage_flag = (
        when(
            (upper(col("account_value_tier")) == lit("HIGH"))
            & (col("potential_value_usd") > lit(0))
            & ((col("actual_value_usd") / col("potential_value_usd")) < lit(0.25))
            & (touch_count <= lit(2)),
            lit("Under-served high-value"),
        )
        .when(
            (upper(col("account_value_tier")) == lit("HIGH"))
            & (touch_count >= lit(3))
            & (pos_count == touch_count),
            lit("Well-served high-value"),
        )
        .when(
            (upper(col("account_value_tier")) == lit("LOW"))
            & (f2f_count >= lit(1))
            & (neg_no_resp >= lit(1)),
            lit("Over-served low-value"),
        )
        .otherwise(lit("Adequate"))
    )

    result = joined.select(
        account["account_id"].alias("account_id"),
        col("account_value_tier"),
        col("segment"),
        col("specialty"),
        account["territory_id"].alias("territory_id"),
        col("potential_value_usd"),
        col("actual_value_usd"),
        (col("potential_value_usd") - col("actual_value_usd")).alias("value_gap_usd"),
        realization_ratio.alias("realization_ratio"),
        touch_count.alias("touch_count"),
        total_cost.alias("total_cost_usd"),
        avg_engagement.alias("avg_engagement_score"),
        positive_rate.alias("positive_rate"),
        coverage_flag.alias("coverage_flag"),
    )

    # The caller TRUNCATEd the target above so the NXD-managed table schema is
    # preserved; append rather than overwrite (which would drop+recreate it).
    result.write.mode("append").save_as_table(target_table)

    written = session.table(target_table).count()
    return f"{written} account_coverage rows written to {target_table}"
$$;

-- Reset the target so a partial run can't leave stale rows alongside fresh ones.
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].account_coverage }};

CALL COMPUTE_ACCOUNT_COVERAGE(
    '{{ inputs.data_products["crm-activity"].snowflake.account }}',
    '{{ inputs.data_products["crm-activity"].snowflake.activity }}',
    '{{ outputs["snowflake"].account_coverage }}'
);
