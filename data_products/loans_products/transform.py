from nxd.core.context import Snowflake
from snowflake.connector import connect

TABLES = ["TERM_DEPOSITS", "HOME_LOAN_RATES"]


def transform(
    product_competitiveness: Snowflake,
    snowflake: Snowflake,
) -> None:
    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()
    for table_name in TABLES:
        cursor.execute(
            f"""
            CREATE OR REPLACE TABLE {snowflake.schema}.{table_name} AS
                SELECT *
                FROM {product_competitiveness.schema}.{table_name}
                WHERE bank = 'Westpac'
        """
        )
    cursor.close()
    conn.close()
