"""Soda quality check transform for the streaming-transactions Databricks table.

Runs every 5 minutes (triggered by schedule on the source-aligned input).
After the Soda checks pass, copies the latest rows from STREAMING_TRANSACTIONS
to SODA_VERIFIED_TRANSACTIONS so downstream consumers know the data is clean.
"""

import logging

import requests
from databricks import sql as dbsql  # type: ignore[reportAttributeAccessIssue]
from nxd import data_product
from nxd.core.context import DatabricksRead
from nxd.core.context import DatabricksWrite

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Azure resource ID for Databricks (constant across all Azure tenants)
_DATABRICKS_SCOPE = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default"


def _get_sp_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Get an OAuth2 access token for Databricks using Azure service principal credentials."""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    response = requests.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": _DATABRICKS_SCOPE,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _get_access_token(output: DatabricksWrite) -> str:
    """Resolve the access token for DBSQL, handling both PAT and Service Principal auth."""
    if output.private_access_token is not None:
        return output.private_access_token

    if output.tenant_id and output.principal_id and output.principal_secret:
        logger.info("Generating OAuth token from service principal credentials")
        return _get_sp_token(output.tenant_id, output.principal_id, output.principal_secret)

    raise ValueError(
        "DatabricksWrite context has no usable auth credentials "
        "(neither private_access_token nor service principal fields are set)"
    )


@data_product.on_transform()
def transform(
    databricks_source: DatabricksRead,
    databricks_output: DatabricksWrite,
) -> None:
    """Copy Soda-verified rows from STREAMING_TRANSACTIONS to SODA_VERIFIED_TRANSACTIONS."""
    source_table = databricks_source.full_table_name("output_model")
    output_table = databricks_output.full_table_name("soda_verified_transactions")

    logger.info(f"Soda checks passed — copying {source_table} → {output_table}")

    access_token = _get_access_token(databricks_output)

    with dbsql.connect(
        server_hostname=databricks_output.host,
        http_path=databricks_output.http_path,
        access_token=access_token,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE OR REPLACE TABLE {output_table} AS SELECT * FROM {source_table}")

    logger.info(f"Written {output_table} successfully")


if __name__ == "__main__":
    data_product.main()
