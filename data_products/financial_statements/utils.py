import logging
from io import BytesIO
from io import StringIO

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from nxd.data_product.context import API
from nxd.data_product.context import AzureDataLakeStorage

# Define explicit PyArrow schema for source_documents to match model definition
SOURCE_DOCUMENTS_SCHEMA = pa.schema(
    [
        pa.field("id", pa.int32()),
        pa.field("filename", pa.string()),
        pa.field("document_type", pa.string()),
        pa.field("url", pa.string()),
    ]
)


def get_logger():
    _logger = logging.getLogger("utils")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
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
    return DataLakeServiceClient(
        f"https://{context.account_name}.dfs.core.windows.net", credential=credentials
    )


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


def read_from_adls(adls_context: AzureDataLakeStorage, model_name: str) -> pd.DataFrame:
    """Read data from Azure Data Lake Storage."""
    service_client = _get_adls_client(adls_context)
    file_system_client = service_client.get_file_system_client(
        file_system=adls_context.container
    )

    # Try to get model path, handle different attribute names
    if hasattr(adls_context, "model_paths") and model_name in adls_context.model_paths:
        file_path = adls_context.model_paths[model_name].path
    else:
        # Fallback: construct a reasonable path
        file_path = f"{model_name}.csv"

    full_path = f"https://{adls_context.account_name}.dfs.core.windows.net/{adls_context.container}/{file_path}"
    _logger.info(f"Reading data to ADLS at path: {file_path}")
    _logger.info(f"Full ADLS path: {full_path}")

    file_client = file_system_client.get_file_client(file_path)

    download = file_client.download_file()
    content = download.readall()
    if "parquet" in file_path.lower():
        df = pd.read_parquet(BytesIO(content))
    elif "csv" in file_path.lower():
        content = content.decode("utf-8")
        df = pd.read_csv(StringIO(content))
    else:
        raise ValueError(f"Unsupported file format for path: {file_path}")
    _logger.info(f"Successfully read {len(df)} rows from ADLS: {file_path}")
    return df


def _retrieve_source_docs(api: API) -> pa.Table:
    """
    Sample CSV content:

    id,filename,document_type,url
    1001,balance-sheet-2025-01.pdf,pdf,https://example.com/balance-sheets/2025-01.pdf
    1002,balance-sheet-2025-03.pdf,pdf,https://example.com/balance-sheets/2025-03.pdf
    1003,balance-sheet-2025-06.pdf,pdf,https://example.com/balance-sheets/2025-06.pdf
    1004,balance-sheet-2025-09.pdf,pdf,https://example.com/balance-sheets/2025-09.pdf
    """
    source_documents = pd.read_csv(
        f"{api.url}/source_documents.csv",
        dtype={"id": np.int32, "filename": str, "document_type": str, "url": str},
    )
    print(source_documents.head())

    return pa.Table.from_pandas(source_documents, schema=SOURCE_DOCUMENTS_SCHEMA)
