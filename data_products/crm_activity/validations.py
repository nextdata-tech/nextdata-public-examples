import logging

from nxd.data_product.context import Snowflake
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum
from snowflake.connector import connect

_logger = logging.getLogger("contracts")
_logger.setLevel(logging.INFO)


def _snowflake_connect(snowflake: Snowflake):
    """Open a Snowflake connection from the verification context."""
    return connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )


def email_opt_in_missing(
    snowflake: Snowflake,
) -> VerifyResult:
    """Warn when the email_opt_in field is null on the account model."""
    _logger.info("Starting verification")

    model = "account"
    field = "email_opt_in"
    table_name = snowflake.model_tables[model]

    conn = _snowflake_connect(snowflake)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT COUNT(*) AS total, "
                f"SUM(CASE WHEN {field} IS NULL THEN 1 ELSE 0 END) AS missing "
                f"FROM {table_name}"
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
    finally:
        conn.close()

    total_count = int(row[0]) if row and row[0] is not None else 0
    missing_count = int(row[1]) if row and row[1] is not None else 0
    missing_pct = round(100.0 * missing_count / total_count, 2) if total_count else 0.0
    msg = f"{missing_pct}% of accounts have a missing {field} value"

    result_enum = VerifyResultEnum.PASS
    if missing_count > 0:
        _logger.warning(f"Null values found in '{field}': {msg}")
        result_enum = VerifyResultEnum.WARNING

    _logger.info("End verification")
    return VerifyResult(
        result=result_enum,
        context={
            "details": [
                {
                    "model": model,
                    "table": table_name,
                    "fields_checked": [field],
                    "email_opt_in_stats": {
                        field: msg,
                        "total": total_count,
                        "missing": missing_count,
                    },
                }
            ],
        },
    )


def orphan_activity(
    snowflake: Snowflake,
) -> VerifyResult:
    """Warn when activity rows reference an account_id that does not exist in the account model."""
    _logger.info("Starting verification")

    account_table = snowflake.model_tables["account"]
    activity_table = snowflake.model_tables["activity"]

    conn = _snowflake_connect(snowflake)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT COUNT(*) AS total, "
                f"SUM(CASE WHEN c.account_id IS NULL THEN 1 ELSE 0 END) AS orphans "
                f"FROM {activity_table} a "
                f"LEFT JOIN {account_table} c ON a.account_id = c.account_id"
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
    finally:
        conn.close()

    total_count = int(row[0]) if row and row[0] is not None else 0
    orphan_count = int(row[1]) if row and row[1] is not None else 0
    orphan_pct = round(100.0 * orphan_count / total_count, 2) if total_count else 0.0
    msg = f"{orphan_pct}% of activities reference an unknown account_id"

    result_enum = VerifyResultEnum.PASS
    if orphan_count > 0:
        _logger.warning(f"Orphan activities found: {msg}")
        result_enum = VerifyResultEnum.WARNING

    _logger.info("End verification")
    return VerifyResult(
        result=result_enum,
        context={
            "details": [
                {
                    "model": "activity",
                    "table": activity_table,
                    "joined_to": account_table,
                    "fields_checked": ["account_id"],
                    "orphan_activity_stats": {
                        "summary": msg,
                        "total": total_count,
                        "orphans": orphan_count,
                    },
                }
            ],
        },
    )


def invalid_npi(
    snowflake: Snowflake,
) -> VerifyResult:
    """Warn when an account's npi is null or not exactly 10 digits."""
    _logger.info("Starting verification")

    model = "account"
    field = "npi"
    table_name = snowflake.model_tables[model]

    conn = _snowflake_connect(snowflake)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT COUNT(*) AS total, "
                f"SUM(CASE WHEN {field} IS NULL "
                f"OR LENGTH(TO_VARCHAR({field})) <> 10 THEN 1 ELSE 0 END) AS invalid "
                f"FROM {table_name}"
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
    finally:
        conn.close()

    total_count = int(row[0]) if row and row[0] is not None else 0
    invalid_count = int(row[1]) if row and row[1] is not None else 0
    invalid_pct = round(100.0 * invalid_count / total_count, 2) if total_count else 0.0
    msg = f"{invalid_pct}% of accounts have an npi that is null or not 10 digits"

    result_enum = VerifyResultEnum.PASS
    if invalid_count > 0:
        _logger.warning(f"Invalid npi values found: {msg}")
        result_enum = VerifyResultEnum.WARNING

    _logger.info("End verification")
    return VerifyResult(
        result=result_enum,
        context={
            "details": [
                {
                    "model": model,
                    "table": table_name,
                    "fields_checked": [field],
                    "invalid_npi_stats": {
                        "summary": msg,
                        "total": total_count,
                        "invalid": invalid_count,
                    },
                }
            ],
        },
    )


def inconsistent_casing(
    snowflake: Snowflake,
) -> VerifyResult:
    """Warn when first_name / last_name / status differ from their InitCap form."""
    _logger.info("Starting verification")

    model = "account"
    fields = ["first_name", "last_name", "status"]
    table_name = snowflake.model_tables[model]

    conn = _snowflake_connect(snowflake)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT COUNT(*) AS total, "
                f"SUM(CASE WHEN "
                f"(first_name IS NOT NULL AND first_name <> INITCAP(first_name)) "
                f"OR (last_name IS NOT NULL AND last_name <> INITCAP(last_name)) "
                f"OR (status IS NOT NULL AND status <> INITCAP(status)) "
                f"THEN 1 ELSE 0 END) AS bad "
                f"FROM {table_name}"
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
    finally:
        conn.close()

    total_count = int(row[0]) if row and row[0] is not None else 0
    bad_count = int(row[1]) if row and row[1] is not None else 0
    bad_pct = round(100.0 * bad_count / total_count, 2) if total_count else 0.0
    msg = f"{bad_pct}% of accounts have non-canonical casing in first_name / last_name / status"

    result_enum = VerifyResultEnum.PASS
    if bad_count > 0:
        _logger.warning(f"Inconsistent casing found: {msg}")
        result_enum = VerifyResultEnum.WARNING

    _logger.info("End verification")
    return VerifyResult(
        result=result_enum,
        context={
            "details": [
                {
                    "model": model,
                    "table": table_name,
                    "fields_checked": fields,
                    "inconsistent_casing_stats": {
                        "summary": msg,
                        "total": total_count,
                        "bad": bad_count,
                    },
                }
            ],
        },
    )


def inactive_account_with_activity(
    snowflake: Snowflake,
) -> VerifyResult:
    """Warn when accounts marked Inactive still have logged activity rows."""
    _logger.info("Starting verification")

    account_table = snowflake.model_tables["account"]
    activity_table = snowflake.model_tables["activity"]

    conn = _snowflake_connect(snowflake)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT COUNT(DISTINCT c.account_id) AS bad_accounts, "
                f"COUNT(a.activity_id) AS bad_activities "
                f"FROM {account_table} c "
                f"JOIN {activity_table} a ON a.account_id = c.account_id "
                f"WHERE UPPER(c.status) = 'INACTIVE'"
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
    finally:
        conn.close()

    bad_accounts = int(row[0]) if row and row[0] is not None else 0
    bad_activities = int(row[1]) if row and row[1] is not None else 0
    msg = (
        f"{bad_accounts} inactive accounts have {bad_activities} logged activities"
    )

    result_enum = VerifyResultEnum.PASS
    if bad_accounts > 0:
        _logger.warning(f"Inactive accounts with activity found: {msg}")
        result_enum = VerifyResultEnum.WARNING

    _logger.info("End verification")
    return VerifyResult(
        result=result_enum,
        context={
            "details": [
                {
                    "model": "account",
                    "table": account_table,
                    "joined_to": activity_table,
                    "fields_checked": ["status", "account_id"],
                    "inactive_account_with_activity_stats": {
                        "summary": msg,
                        "inactive_accounts_with_activity": bad_accounts,
                        "activities_against_inactive_accounts": bad_activities,
                    },
                }
            ],
        },
    )
