from nxd.core.context import Snowflake
from snowflake.connector import connect


def transform(snowflake: Snowflake):
    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()
    cursor.execute(
        f"""
        CREATE OR REPLACE TABLE {snowflake.schema}.BANKS AS
            SELECT 'Westpac' as name
            UNION ALL
            SELECT 'ANZ' as name
            UNION ALL
            SELECT 'Macquarie' as name
    """
    )
    conn.close()
