import io
import logging

import pyarrow.parquet as pq
from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from nxd.data_product.context import AzureDataLakeStorage
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum

_logger = logging.getLogger("contracts.adls_input_check")


def verify(adls: AzureDataLakeStorage) -> VerifyResult:
    """Verify that the incoming ADLS input contains at least one record."""
    credentials = ClientSecretCredential(adls.tenant_id, adls.client_id, adls.client_secret)
    service_client = DataLakeServiceClient(f"https://{adls.account_name}.dfs.core.windows.net", credential=credentials)
    results = {}
    failed = False
    for model_name, model_path_info in adls.model_paths.items():
        path = model_path_info.path
        try:
            file_client = service_client.get_file_client(file_system=adls.container, file_path=path)
            content = file_client.download_file().readall()
            table = pq.read_table(io.BytesIO(content))
            row_count = table.num_rows
            results[model_name] = {"path": path, "row_count": row_count}
            if row_count == 0:
                _logger.warning(f"Input model '{model_name}' contains no records")
                failed = True
        except Exception as e:
            _logger.error(f"Failed to read input model '{model_name}': {e}")
            results[model_name] = {"path": path, "error": str(e)}
            failed = True
    if failed:
        return VerifyResult(VerifyResultEnum.FAILED, {"results": results})
    return VerifyResult(VerifyResultEnum.PASS, {"results": results})
