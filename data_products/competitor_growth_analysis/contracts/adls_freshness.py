import io
import logging

import pyarrow.parquet as pq
from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from nxd.data_product.context import AzureDataLakeStorage
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum

_logger = logging.getLogger("contracts.adls_freshness")


def verify(adls: AzureDataLakeStorage) -> VerifyResult:
    """Verify that every promised model in ADLS contains at least one record."""
    credentials = ClientSecretCredential(adls.tenant_id, adls.client_id, adls.client_secret)
    service_client = DataLakeServiceClient(f"https://{adls.account_name}.dfs.core.windows.net", credential=credentials)

    results = {}
    failed = False

    for model_name, model_path_info in adls.model_paths.items():
        path = model_path_info.path
        try:
            if path.endswith(".parquet"):
                file_client = service_client.get_file_client(file_system=adls.container, file_path=path)
                download = file_client.download_file()
                content = download.readall()
                table = pq.read_table(io.BytesIO(content))
                row_count = table.num_rows
            else:
                # Non-Parquet path (e.g. JSON glob directory) — count files under the prefix
                fs_client = service_client.get_file_system_client(adls.container)
                prefix = path.rstrip("/").split("*")[0]
                paths = list(fs_client.get_paths(path=prefix, recursive=True))
                row_count = sum(1 for p in paths if not p.is_directory)

            results[model_name] = {"path": path, "row_count": row_count}
            if row_count == 0:
                _logger.warning(f"Model '{model_name}' at {path} has 0 rows.")
                failed = True
            else:
                _logger.info(f"Model '{model_name}' at {path} has {row_count} rows.")
        except Exception as e:
            _logger.error(f"Failed to read model '{model_name}' at {path}: {e}")
            results[model_name] = {"path": path, "error": str(e)}
            failed = True

    if failed:
        return VerifyResult(VerifyResultEnum.FAILED, {"results": results})
    return VerifyResult(VerifyResultEnum.PASS, {"results": results})
