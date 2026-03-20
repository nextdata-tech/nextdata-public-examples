import json

from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from nxd.core.yaml_schemas import Model
from nxd.data_product.context import AzureDataLakeStorage
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum

EXPECTED_PORTOFOLIOS = {"HLLVR3", "HL", "HLLVR3"}


def verify(
    market_rates: AzureDataLakeStorage, models: dict[str, Model]
) -> VerifyResult:
    adls = DataLakeServiceClient(
        f"https://{market_rates.account_name}.dfs.core.windows.net",
        ClientSecretCredential(
            tenant_id=market_rates.tenant_id,
            client_id=market_rates.client_id,
            client_secret=market_rates.client_secret,
        ),
    )
    model_name = models.keys()[0]
    model = models[model_name]
    file_client = adls.get_file_client(market_rates.container, model.path)
    file_contents = file_client.download_file().readall().decode()
    portfolio_ids = set(
        [json.loads(line)["PortfolioId"] for line in file_contents.splitlines()]
    )

    if portfolio_ids.difference(EXPECTED_PORTOFOLIOS):
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {"received": list(portfolio_ids), "expected": list(EXPECTED_PORTOFOLIOS)},
        )
    else:
        return VerifyResult(
            VerifyResultEnum.PASS,
            {"portfolios": list(portfolio_ids)},
        )
