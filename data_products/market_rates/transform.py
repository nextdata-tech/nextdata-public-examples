import logging

from api import anz
from api import macquarie
from api import westpac
from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeFileClient
from azure.storage.filedatalake import DataLakeServiceClient
from nxd.core.context import API
from nxd.core.context import AzureDataLakeStorage

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)


def _get_data_lake_file_client(
    adls: AzureDataLakeStorage, model_name: str
) -> DataLakeFileClient:
    credentials = ClientSecretCredential(
        tenant_id=adls.tenant_id,
        client_id=adls.client_id,
        client_secret=adls.client_secret,
    )
    adls_client = DataLakeServiceClient(
        f"https://{adls.account_name}.dfs.core.windows.net", credentials
    )
    model_path = adls.model_paths[model_name].path
    file_client = adls_client.get_file_client(adls.container, model_path)
    return file_client


def transform(
    comp_public: API,
    nextopia_public: API,
    comp2_public: API,
    adls: AzureDataLakeStorage,
) -> None:
    _logger.info("Starting transform")

    # ANZ
    anz_product_file_client = _get_data_lake_file_client(
        adls, model_name="anz_products"
    )
    anz.sync_product_data(anz_product_file_client)

    # Westpac
    westpac_term_deposits_file_client = _get_data_lake_file_client(
        adls, model_name="westpac_term_deposits"
    )
    westpac.sync_term_deposit_data(westpac_term_deposits_file_client)

    westpac_home_loans_file_client = _get_data_lake_file_client(
        adls, model_name="westpac_home_loans"
    )
    westpac.sync_home_loan_data(westpac_home_loans_file_client)

    # Macquarie
    macquarie_term_deposits_file_client = _get_data_lake_file_client(
        adls, model_name="macquarie_term_deposits"
    )
    macquarie.sync_term_deposit_data(macquarie_term_deposits_file_client)

    macquarie_home_loan_file_client = _get_data_lake_file_client(
        adls, model_name="macquarie_home_loans"
    )
    macquarie.sync_home_loan_data(macquarie_home_loan_file_client)

    _logger.info("Transform completed successfully")
