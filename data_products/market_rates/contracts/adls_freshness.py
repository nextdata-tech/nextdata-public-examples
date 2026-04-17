import logging
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from nxd.data_product.context import AzureDataLakeStorage
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum

_logger = logging.getLogger("contracts.adls_freshness")

MAX_FILE_AGE_HOURS = 24


def _latest_update_timestamp(
    service_client: DataLakeServiceClient,
    file_system: str,
    path: str,
) -> datetime:
    normalized_path = path.rstrip("/")

    try:
        file_client = service_client.get_file_client(
            file_system=file_system,
            file_path=normalized_path,
        )
        properties = file_client.get_file_properties()
        if properties.last_modified is not None:
            return properties.last_modified.astimezone(timezone.utc)
    except Exception:
        pass

    fs_client = service_client.get_file_system_client(file_system)
    prefix = normalized_path.split("*")[0].rstrip("/")
    latest_modified = None

    for item in fs_client.get_paths(path=prefix, recursive=True):
        if item.is_directory:
            continue
        item_last_modified = item.last_modified.astimezone(timezone.utc)
        if latest_modified is None or item_last_modified > latest_modified:
            latest_modified = item_last_modified

    if latest_modified is None:
        raise FileNotFoundError(f"No files found at path '{path}'")

    return latest_modified


def verify(adls: AzureDataLakeStorage) -> VerifyResult:
    """Verify that every promised model in ADLS was updated within the last 24 hours."""
    credentials = ClientSecretCredential(
        adls.tenant_id,
        adls.client_id,
        adls.client_secret,
    )
    service_client = DataLakeServiceClient(
        f"https://{adls.account_name}.dfs.core.windows.net",
        credential=credentials,
    )

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_FILE_AGE_HOURS)
    results = {}
    failed = False

    for model_name, model_path_info in adls.model_paths.items():
        path = model_path_info.path
        try:
            last_modified = _latest_update_timestamp(service_client, adls.container, path)
            age_hours = round((now - last_modified).total_seconds() / 3600, 2)
            is_fresh = last_modified >= cutoff

            results[model_name] = {
                "path": path,
                "last_modified": last_modified.isoformat(),
                "age_hours": age_hours,
                "max_age_hours": MAX_FILE_AGE_HOURS,
                "fresh": is_fresh,
            }

            if not is_fresh:
                _logger.warning(f"Model '{model_name}' at {path} is stale: last modified {age_hours} hours ago.")
                failed = True
            else:
                _logger.info(f"Model '{model_name}' at {path} is fresh: last modified {age_hours} hours ago.")
        except Exception as e:
            _logger.error(f"Failed to inspect model '{model_name}' at {path}: {e}")
            results[model_name] = {"path": path, "error": str(e), "fresh": False}
            failed = True

    if failed:
        return VerifyResult(VerifyResultEnum.FAILED, {"results": results})
    return VerifyResult(VerifyResultEnum.PASS, {"results": results})
