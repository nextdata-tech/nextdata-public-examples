from databricks import sql
from nxd.core.context import DatabricksWrite
from nxd.core.context import Snowflake
from snowflake.connector import connect

TABLES = ["TERM_DEPOSITS", "HOME_LOAN_RATES"]


def transform(
    product_competitiveness: Snowflake,
    nxd_databricks_storage: DatabricksWrite,
) -> None:
    snowflake_conn = connect(
        user=product_competitiveness.user,
        password=product_competitiveness.password,
        account=product_competitiveness.account,
        warehouse=product_competitiveness.warehouse,
        database=product_competitiveness.database,
        schema=product_competitiveness.schema,
    )
    snowflake_cursor = snowflake_conn.cursor()

    with sql.connect(
        server_hostname=nxd_databricks_storage.host,
        http_path=nxd_databricks_storage.http_path,
        access_token=nxd_databricks_storage.token,
    ) as databricks_conn:
        with databricks_conn.cursor() as databricks_cursor:
            for table_name in TABLES:
                snowflake_cursor.execute(
                    f"SELECT * FROM {product_competitiveness.schema}.{table_name} WHERE bank = 'Westpac'"
                )
                rows = snowflake_cursor.fetchall()
                columns = [desc[0] for desc in snowflake_cursor.description]
                col_defs = ", ".join(f"{col} STRING" for col in columns)
                databricks_cursor.execute(
                    f"CREATE OR REPLACE TABLE {nxd_databricks_storage.full_table_name(table_name)} ({col_defs})"
                )
                if rows:
                    placeholders = ", ".join(["?"] * len(columns))
                    databricks_cursor.executemany(
                        f"INSERT INTO {nxd_databricks_storage.full_table_name(table_name)} VALUES ({placeholders})",
                        rows,
                    )

    snowflake_cursor.close()
    snowflake_conn.close()
