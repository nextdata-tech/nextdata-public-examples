import logging

import requests
from databricks import sql as dbsql
from nxd import data_product
from nxd.core.context import DatabricksWrite

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _get_sp_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Get an OAuth2 access token for Databricks using Azure service principal credentials."""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    response = requests.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
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


@data_product.on_provision()
def provision_tables(databricks: DatabricksWrite):
    """Provision Databricks tables with custom masking functions for trip metrics."""
    trip_metrics_table = databricks.full_table_name("trip_metrics")
    pipeline_summary_table = databricks.full_table_name("pipeline_summary")

    logger.info("Starting Databricks table provisioning")

    access_token = _get_access_token(databricks)

    with dbsql.connect(
        server_hostname=databricks.host,
        http_path=databricks.http_path,
        access_token=access_token,
    ) as conn:
        with conn.cursor() as cursor:
            # Create trip metrics table
            cursor.execute(
                f"""CREATE TABLE IF NOT EXISTS {trip_metrics_table} (
                    pickup_zip STRING NOT NULL, 
                    trip_count INT NOT NULL, 
                    avg_fare DOUBLE NOT NULL
                ) USING DELTA;"""
            )
            logger.info(f"Provisioned table: {trip_metrics_table}")

            # Create pipeline summary table
            cursor.execute(
                f"""CREATE TABLE IF NOT EXISTS {pipeline_summary_table} (
                    pipeline STRING NOT NULL, 
                    status STRING NOT NULL, 
                    rows_processed INT NOT NULL
                ) USING DELTA;"""
            )
            logger.info(f"Provisioned table: {pipeline_summary_table}")

            # Requires CREATE FUNCTION privilege on the schema
            # mask_function = f"{trip_metrics_table}_pickup_zip_mask"
            # Create masking function for sensitive pickup locations
            # cursor.execute(
            #     f"""CREATE OR REPLACE FUNCTION {mask_function}(pickup_zip STRING)
            #     RETURN CASE WHEN pickup_zip = '43016' THEN '*****' ELSE pickup_zip END;"""
            # )
            # logger.info(f"Created masking function: {mask_function}")

            # Apply mask to trip_metrics table
            # cursor.execute(
            #     f"ALTER TABLE {trip_metrics_table} ALTER COLUMN pickup_zip SET MASK {mask_function};"
            # )

            conn.commit()
            logger.info("Table provisioning completed successfully")

    logger.info("Provisioned successfully")


if __name__ == "__main__":
    data_product.provision()
