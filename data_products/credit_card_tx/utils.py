from io import BytesIO

import pyarrow as pa
import pyarrow.parquet as pq
from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from nxd.data_product.context import AzureDataLakeStorage


def _get_adls_client(context: AzureDataLakeStorage) -> DataLakeServiceClient:
    credentials = ClientSecretCredential(
        context.tenant_id,
        context.client_id,
        context.client_secret,
    )
    return DataLakeServiceClient(f"https://{context.account_name}.dfs.core.windows.net", credential=credentials)


def parquet_to_adls(
    context: AzureDataLakeStorage,
    table: pa.Table,
    file_path: str,
) -> None:
    client = _get_adls_client(context)

    file_client = client.get_file_client(
        file_system=context.container,
        file_path=file_path,
    )

    buffer = BytesIO()
    pq.write_table(table, buffer)
    buffer.seek(0)

    file_client.upload_data(buffer, overwrite=True)


def adls_to_parquet(
    context: AzureDataLakeStorage,
    file_path: str,
) -> pa.Table:
    client = _get_adls_client(context)

    file_client = client.get_file_client(
        file_system=context.container,
        file_path=file_path,
    )

    # check if file exists
    if not file_client.exists():
        raise FileNotFoundError(f"File not found in ADLS: {file_path}")

    file = file_client.download_file().readall()
    reader = pa.BufferReader(file)

    return pq.read_table(reader)
