import logging

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from nxd import data_product
from nxd.data_product.context import AzureDataLakeStorage
from nxd.data_product.context import Model
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum

_logger = logging.getLogger("transform.contracts")
_logger.setLevel(logging.INFO)


def _get_adls_client(context: AzureDataLakeStorage) -> DataLakeServiceClient:
    credentials = ClientSecretCredential(
        context.tenant_id,
        context.client_id,
        context.client_secret,
    )
    return DataLakeServiceClient(
        f"https://{context.account_name}.dfs.core.windows.net", credential=credentials
    )


def adls_to_parquet(
    context: AzureDataLakeStorage,
    file_path: str,
) -> pa.Table:
    client = _get_adls_client(context)

    file_client = client.get_file_client(
        file_system=context.container,
        file_path=file_path,
    )

    file = file_client.download_file().readall()
    reader = pa.BufferReader(file)

    return pq.read_table(reader)


@data_product.on_verify()
def verify(
    input: AzureDataLakeStorage,
    models: dict[str, Model],  # Is this optional
) -> VerifyResult:
    try:
        table = adls_to_parquet(
            context=input,
            file_path=input.model_paths["customers"].path,
        )

        # simplistic pii detection
        mask = pc.match_substring(table["email"], "@")  # type: ignore

        if pc.any(mask).as_py():  # type: ignore
            return VerifyResult(
                VerifyResultEnum.FAILED,
                {
                    "result": "Promise failed. Unredacted emails present within `customers`"
                },
            )
        else:
            return VerifyResult(
                VerifyResultEnum.PASS,
                {
                    "result": "Promise fulfilled. No email local-parts present within `customers`"
                },
            )

    except Exception as e:
        _logger.info(f"Unexpected error: {e}")
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {"result": f"Promise failed. Unexpected error: {e}"},
        )


if __name__ == "__main__":
    data_product.verify()
