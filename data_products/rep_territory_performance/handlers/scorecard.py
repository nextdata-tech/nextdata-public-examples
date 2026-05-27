from snowflake.snowpark.functions import avg
from snowflake.snowpark.functions import coalesce
from snowflake.snowpark.functions import col
from snowflake.snowpark.functions import count
from snowflake.snowpark.functions import count_distinct
from snowflake.snowpark.functions import lit
from snowflake.snowpark.functions import round as round_
from snowflake.snowpark.functions import sum as sum_
from snowflake.snowpark.functions import upper
from snowflake.snowpark.functions import when


def build_scorecard(session, activity_table: str, target_table: str) -> str:
    """Rep / territory performance scorecard from the crm-activity ACTIVITY feed.

    Mirrors the previous transform.sql GROUP BY rep_id, territory_id aggregate,
    including the field-vs-HQ campaign flag (MKTG-* reps / T-MKT territory).
    """
    activity = session.table(activity_table)

    grouped = activity.group_by("rep_id", "territory_id").agg(
        count(lit(1)).alias("activity_count"),
        count_distinct("account_id").alias("distinct_accounts"),
        avg("engagement_score").alias("avg_engagement_raw"),
        sum_(when(col("response") == lit("Positive"), lit(1)).otherwise(lit(0))).alias("positive_count"),
        sum_("estimated_cost_usd").alias("total_cost_raw"),
        avg("estimated_cost_usd").alias("avg_cost_raw"),
    )

    activity_count = col("activity_count")

    # ILIKE 'MKTG%' is case-insensitive; upper(...).like(...) preserves that.
    is_hq_campaign = upper(col("rep_id")).like("MKTG%") | (col("territory_id") == lit("T-MKT"))

    avg_engagement_score = coalesce(round_(col("avg_engagement_raw"), lit(2)), lit(0))
    positive_rate = when(
        activity_count > lit(0),
        round_(col("positive_count") / activity_count, lit(4)),
    ).otherwise(lit(0))
    avg_cost_per_activity = coalesce(round_(col("avg_cost_raw"), lit(2)), lit(0))

    result = grouped.select(
        col("rep_id"),
        col("territory_id"),
        is_hq_campaign.alias("is_hq_campaign"),
        activity_count.alias("activity_count"),
        col("distinct_accounts"),
        avg_engagement_score.alias("avg_engagement_score"),
        positive_rate.alias("positive_rate"),
        coalesce(col("total_cost_raw"), lit(0)).alias("total_cost_usd"),
        avg_cost_per_activity.alias("avg_cost_per_activity_usd"),
    )

    # The caller TRUNCATEd the target above so the NXD-managed table schema is
    # preserved; append rather than overwrite (which would drop+recreate it).
    result.write.mode("append").save_as_table(target_table)

    written = session.table(target_table).count()
    return f"{written} rep_territory_scorecard rows written to {target_table}"
