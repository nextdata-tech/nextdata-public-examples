from databricks import sql
from nxd.core.context import DatabricksWrite


def transform(nxd_databricks_storage: DatabricksWrite):
    with sql.connect(
        server_hostname=nxd_databricks_storage.host,
        http_path=nxd_databricks_storage.http_path,
        access_token=nxd_databricks_storage.token,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                CREATE OR REPLACE TABLE {nxd_databricks_storage.full_table_name("BANKS")} AS
                    SELECT 'Westpac' as name
                    UNION ALL
                    SELECT 'ANZ' as name
                    UNION ALL
                    SELECT 'Macquarie' as name
            """
            )
