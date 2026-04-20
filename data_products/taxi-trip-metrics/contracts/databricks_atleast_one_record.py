from databricks import sql
from nxd.data_product.context import DatabricksRead
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum


def verify(nxd_databricks_storage: DatabricksRead) -> VerifyResult:
    """Verify that every promised Databricks table contains at least one record."""
    results = []
    errors = False
    with sql.connect(
        server_hostname=nxd_databricks_storage.host,
        http_path=nxd_databricks_storage.http_path,
        access_token=nxd_databricks_storage.token,
    ) as conn:
        with conn.cursor() as cursor:
            for model_name, table_name in nxd_databricks_storage.model_tables.items():
                fqdn_table_name = nxd_databricks_storage.full_table_name(model_name)
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {fqdn_table_name}")
                data = cursor.fetchone()
                count = data[0] if data else 0
                results.append(
                    {
                        "model_name": model_name,
                        "table_name": fqdn_table_name,
                        "count": count,
                    }
                )
                if count == 0:
                    errors = True

    if errors:
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {"results": results},
        )
    return VerifyResult(
        VerifyResultEnum.PASS,
        {"results": results},
    )
