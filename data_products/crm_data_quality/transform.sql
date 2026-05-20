CREATE OR REPLACE TEMPORARY PROCEDURE COMPUTE_DATA_QUALITY_FINDINGS(
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
    col, lit, count, length, upper, initcap, to_varchar, concat, coalesce,
)


def main(session, account_table: str, activity_table: str, target_table: str) -> str:
    account = session.table(account_table)
    activity = session.table(activity_table)

    # Pre-rename the join key on the activity side so every downstream
    # reference to ACCOUNT_ID is unambiguous, even after group_by/agg (which
    # otherwise keeps both copies of the column in the post-join schema).
    activity_j = activity.with_column_renamed("account_id", "act_account_id")

    # 1. orphan_activity - activity references an unknown account_id.
    orphans = (
        activity_j.join(
            account,
            activity_j["act_account_id"] == account["account_id"],
            "left",
        )
        .filter(account["account_id"].is_null())
        .select(
            lit("orphan_activity").alias("finding_type"),
            lit("activity").alias("entity_type"),
            activity_j["activity_id"].alias("entity_id"),
            concat(
                lit("activity references unknown account_id "),
                activity_j["act_account_id"],
            ).alias("detail"),
        )
    )

    # 2. invalid_npi - npi missing or not a 10-digit identifier.
    invalid_npi = account.filter(
        col("npi").is_null() | (length(to_varchar(col("npi"))) != lit(10))
    ).select(
        lit("invalid_npi").alias("finding_type"),
        lit("account").alias("entity_type"),
        col("account_id").alias("entity_id"),
        concat(
            lit("npi "),
            coalesce(to_varchar(col("npi")), lit("<null>")),
            lit(" is not a 10-digit identifier"),
        ).alias("detail"),
    )

    # 3. inconsistent_casing - non-canonical first_name / last_name / status.
    casing = account.filter(
        (col("first_name").is_not_null() & (col("first_name") != initcap(col("first_name"))))
        | (col("last_name").is_not_null() & (col("last_name") != initcap(col("last_name"))))
        | (col("status").is_not_null() & (col("status") != initcap(col("status"))))
    ).select(
        lit("inconsistent_casing").alias("finding_type"),
        lit("account").alias("entity_type"),
        col("account_id").alias("entity_id"),
        lit("non-canonical casing in first_name / last_name / status").alias("detail"),
    )

    # 4. missing_email_opt_in - opt-in flag is null.
    missing_opt_in = account.filter(col("email_opt_in").is_null()).select(
        lit("missing_email_opt_in").alias("finding_type"),
        lit("account").alias("entity_type"),
        col("account_id").alias("entity_id"),
        lit("email_opt_in is null").alias("detail"),
    )

    # 5. inactive_account_with_activity - Inactive account that still has activity.
    # Reuse the renamed-key activity frame so the join doesn't leave two
    # ACCOUNT_ID columns lurking in the post-aggregate schema.
    inactive_grouped = (
        account.join(
            activity_j,
            account["account_id"] == activity_j["act_account_id"],
            "inner",
        )
        .filter(upper(account["status"]) == lit("INACTIVE"))
        .group_by(account["account_id"])
        .agg(count(activity_j["activity_id"]).alias("activity_count"))
    )
    inactive = inactive_grouped.select(
        lit("inactive_account_with_activity").alias("finding_type"),
        lit("account").alias("entity_type"),
        col("account_id").alias("entity_id"),
        concat(
            lit("account status is Inactive but has "),
            to_varchar(col("activity_count")),
            lit(" activities"),
        ).alias("detail"),
    )

    findings = (
        orphans
        .union_all(invalid_npi)
        .union_all(casing)
        .union_all(missing_opt_in)
        .union_all(inactive)
    )

    # The caller TRUNCATEd the target above so the NXD-managed table schema is
    # preserved; append rather than overwrite (which would drop+recreate it).
    findings.write.mode("append").save_as_table(target_table)

    written = session.table(target_table).count()
    return f"{written} findings written to {target_table}"
$$;

-- Reset the target so a partial run can't leave stale rows alongside fresh ones.
TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].data_quality_findings }};

CALL COMPUTE_DATA_QUALITY_FINDINGS(
    '{{ inputs.data_products["crm-activity"].snowflake.account }}',
    '{{ inputs.data_products["crm-activity"].snowflake.activity }}',
    '{{ outputs["snowflake"].data_quality_findings }}'
);
