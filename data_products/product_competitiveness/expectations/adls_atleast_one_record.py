import json

from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from nxd.data_product.context import AzureDataLakeStorage
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum


def _count_records(file_contents: str) -> int:
    """Count records in a JSON output file, tolerating either shape a
    producer may write: a single JSON value (e.g. a whole array on one
    line) or NDJSON (one JSON value per line)."""
    stripped = file_contents.strip()
    if not stripped:
        return 0
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        pass
    else:
        return len(value) if isinstance(value, list) else 1
    # Not a single parseable JSON value — try NDJSON, one record per line.
    return len([json.loads(line) for line in stripped.splitlines()])


def verify(market_rates: AzureDataLakeStorage) -> VerifyResult:
    adls = DataLakeServiceClient(
        f"https://{market_rates.account_name}.dfs.core.windows.net",
        ClientSecretCredential(
            tenant_id=market_rates.tenant_id,
            client_id=market_rates.client_id,
            client_secret=market_rates.client_secret,
        ),
    )
    record_counts = {}
    errors = {}
    for model_name, model in market_rates.model_paths.items():
        print(f"Verify model has atleast one record. ({model_name=}, {model.path=})")
        try:
            file_client = adls.get_file_client(market_rates.container, model.path)
            file_contents = file_client.download_file().readall().decode()
            num_records = _count_records(file_contents)
        except Exception as e:  # noqa: BLE001 - one bad upstream model must not crash the whole check
            errors[model_name] = f"{type(e).__name__}: {e}"
            continue
        record_counts[model_name] = num_records
        if num_records == 0:
            errors[model_name] = "0 records"

    if errors:
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {"errors": json.dumps(errors), "record_counts": json.dumps(record_counts)},
        )
    else:
        return VerifyResult(
            VerifyResultEnum.PASS,
            {"record_counts": json.dumps(record_counts)},
        )
