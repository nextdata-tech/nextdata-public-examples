import json
import logging
from io import BytesIO

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from langchain.docstore.document import Document
from nxd.data_product.context import AzureDataLakeStorage
from nxd.data_product.context import Snowflake
from snowflake import connector
from snowflake.connector.pandas_tools import write_pandas


def get_logger():
    _logger = logging.getLogger("utils")
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)
    _logger.setLevel(logging.INFO)
    return _logger


_logger = get_logger()


def _get_adls_client(context: AzureDataLakeStorage) -> DataLakeServiceClient:
    credentials = ClientSecretCredential(
        context.tenant_id,
        context.client_id,
        context.client_secret,
    )
    return DataLakeServiceClient(f"https://{context.account_name}.dfs.core.windows.net", credential=credentials)


def adls_to_parquet(
    context: AzureDataLakeStorage,
    file_path: str,
) -> pa.Table:
    full_path = f"https://{context.account_name}.dfs.core.windows.net/{context.container}/{file_path}"
    _logger.info(f"Reading parquet data from ADLS at path: {file_path}")
    _logger.info(f"Full ADLS path: {full_path}")
    client = _get_adls_client(context)

    file_client = client.get_file_client(
        file_system=context.container,
        file_path=file_path,
    )

    file = file_client.download_file().readall()
    reader = pa.BufferReader(file)

    return pq.read_table(reader)


def adls_to_bytesio(
    context: AzureDataLakeStorage,
    file_path: str,
) -> BytesIO:
    full_path = f"https://{context.account_name}.dfs.core.windows.net/{context.container}/{file_path}"
    _logger.info(f"Uploading binary data to ADLS at path: {file_path}")
    _logger.info(f"Full ADLS path: {full_path}")
    client = _get_adls_client(context)
    client = _get_adls_client(context)

    file_client = client.get_file_client(
        file_system=context.container,
        file_path=file_path,
    )

    file = file_client.download_file()
    buffer = BytesIO()
    file.readinto(buffer)
    buffer.seek(0)

    return buffer


def parquet_to_adls(
    context: AzureDataLakeStorage,
    table: pa.Table,
    file_path: str,
) -> None:
    full_path = f"https://{context.account_name}.dfs.core.windows.net/{context.container}/{file_path}"
    _logger.info(f"Uploading parquet data to ADLS at path: {file_path}")
    _logger.info(f"Full ADLS path: {full_path}")
    client = _get_adls_client(context)

    file_client = client.get_file_client(
        file_system=context.container,
        file_path=file_path,
    )

    buffer = BytesIO()
    pq.write_table(table, buffer)
    buffer.seek(0)

    file_client.upload_data(buffer, overwrite=True)


def pandas_to_snowflake(
    context: Snowflake,
    dataframe: pd.DataFrame,
    table_name: str,
) -> None:
    # force uppercase columns
    dataframe.columns = dataframe.columns.str.upper()

    with connector.connect(
        user=context.user,
        password=context.password,
        account=context.account,
        warehouse=context.warehouse,
        role=context.role,
        database=context.database,
        schema=context.schema,
        ocsp_fail_open=True,
    ) as conn:
        write_pandas(
            conn,
            dataframe,
            table_name,
            context.database,
            context.schema,
            auto_create_table=False,
            use_logical_type=True,
        )


def documents_to_json_to_adls(
    context: AzureDataLakeStorage,
    documents: list[Document],
    file_path: str,
):
    client = _get_adls_client(context)

    file_client = client.get_file_client(
        file_system=context.container,
        file_path=file_path,
    )

    data = [d.to_json().get("kwargs", {}) for d in documents]

    file_client.upload_data(json.dumps(data), overwrite=True)
