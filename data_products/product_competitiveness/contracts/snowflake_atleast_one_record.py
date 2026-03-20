import json

from nxd.data_product.context import Snowflake
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum
from snowflake.connector import connect


def verify(snowflake: Snowflake) -> VerifyResult:
    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()
    results = []
    errors = False
    for model_name, table_name in snowflake.model_tables.items():
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        data = cursor.fetchone()
        if data:
            results.append(
                {
                    "model_name": model_name,
                    "table_name": table_name,
                    "results": json.dumps(data),
                }
            )
        else:
            errors = True

    cursor.close()
    conn.close()

    if errors:
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {
                "model_name": model_name,
                "table_name": table_name,
                "results": json.dumps(results),
            },
        )

    return VerifyResult(
        VerifyResultEnum.PASS,
        {
            "model_name": model_name,
            "table_name": table_name,
            "results": json.dumps(results),
        },
    )
