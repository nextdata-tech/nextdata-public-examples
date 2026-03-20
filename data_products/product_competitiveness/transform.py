import os
import tempfile

from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeFileClient
from azure.storage.filedatalake import DataLakeServiceClient
from nxd.core.context import AzureDataLakeStorage
from nxd.core.context import Snowflake
from snowflake.connector import connect
from snowflake.connector.cursor import SnowflakeCursor

SQL_TRANSFORM_PATH = "sql/transforms"
SQL_DDL_PATH = "sql/ddl"


def load_table(
    file_client: DataLakeFileClient,
    cursor: SnowflakeCursor,
    model_name: str,
):
    table_name = model_name.upper()
    with open(f"{SQL_DDL_PATH}/{model_name}.sql") as f:
        ddl = f.read()
    with tempfile.NamedTemporaryFile("rb+", suffix=".json") as tmpfile:
        tmpfile.write(file_client.download_file().read())
        tmpfile.seek(0)
        cursor.execute(f"TRUNCATE TABLE IF EXISTS {table_name}")
        cursor.execute(ddl)
        cursor.execute(f"PUT file://{tmpfile.name} @%{table_name} OVERWRITE = TRUE")
        cursor.execute(
            f"""
            COPY INTO {table_name}
            FILE_FORMAT = (TYPE = JSON, STRIP_OUTER_ARRAY = TRUE)
            MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
        """
        )
        cursor.execute(f"REMOVE @%{table_name}")


def transform(market_rates: AzureDataLakeStorage, snowflake: Snowflake):
    print(f"Listing directory: {os.listdir()=}")
    credentials = ClientSecretCredential(
        tenant_id=market_rates.tenant_id,
        client_id=market_rates.client_id,
        client_secret=market_rates.client_secret,
    )
    adls_client = DataLakeServiceClient(
        f"https://{market_rates.account_name}.dfs.core.windows.net", credentials
    )
    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()

    for model_name, model in market_rates.model_paths.items():
        print(f"Loading table ({model_name=})")
        file_client = adls_client.get_file_client(market_rates.container, model.path)
        load_table(file_client, cursor, model_name)
        conn.commit()

    for filename in os.listdir(SQL_TRANSFORM_PATH):
        print(f"Running SQL transform {filename=}")
        with open(f"{SQL_TRANSFORM_PATH}/{filename}") as f:
            cursor.execute(f.read())

    conn.commit()
    conn.close()
