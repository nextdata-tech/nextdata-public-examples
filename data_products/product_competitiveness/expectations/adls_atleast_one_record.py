import json

from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from nxd.data_product.context import AzureDataLakeStorage
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum


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
    for model_name, model in market_rates.model_paths.items():
        print(f"Verify model has atleast one record. ({model_name=}, {model.path=})")
        file_client = adls.get_file_client(market_rates.container, model.path)
        file_contents = file_client.download_file().readall().decode()
        num_records = len([json.loads(line) for line in file_contents.splitlines()])
        record_counts[model_name] = num_records

    errors = {model_name: cnt for model_name, cnt in record_counts.items() if cnt == 0}
    if errors:
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {"errors": json.dumps(errors)},
        )
    else:
        return VerifyResult(
            VerifyResultEnum.PASS,
            {"record_counts": json.dumps(record_counts)},
        )
