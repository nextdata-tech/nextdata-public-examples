from nxd.data_product.context import Snowflake
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum
from snowflake.connector import connect

EXPECTED_BANKS = {"Westpac", "ANZ", "Macquarie"}


def verify(snowflake: Snowflake) -> VerifyResult:
    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()
    results = {}
    errors = {}
    for model_name, table_name in snowflake.model_tables.items():
        cursor.execute(f"SELECT distinct bank FROM {table_name}")
        rows = cursor.fetchall()
        banks = set([row[0] for row in rows])
        if banks.difference(EXPECTED_BANKS):
            errors[model_name] = list(banks)
        else:
            results[model_name] = list(banks)

    cursor.close()
    conn.close()

    if errors:
        return VerifyResult(
            VerifyResultEnum.FAILED,
            errors,
        )

    return VerifyResult(
        VerifyResultEnum.PASS,
        results,
    )
