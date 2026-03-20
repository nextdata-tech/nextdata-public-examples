from nxd.core.context import Snowflake
from nxd.core.yaml_schemas import Field
from nxd.drivers.rpc import Request
from nxd.drivers.rpc import Response
from nxd.drivers.rpc import function
from nxd.drivers.rpc import mcp
from nxd.spec import attribute
from nxd.spec import semantic_model
from nxd.spec.data_types import list
from nxd.spec.data_types import string
from snowflake.connector import connect

get_banks_request = semantic_model(
    "get_banks_request",
    attributes={},
    description="Request to get a list of bank names",
)
get_banks_response = semantic_model(
    "get_banks_response",
    attributes=[
        attribute(
            name="banks",
            data_type=list(
                Field(
                    data_type=string(),
                    name="banks",
                    description="A list of bank names",
                    metadata=None,
                    constraints=None,
                    relates_to=[],
                    semantic_tags=None,
                )
            ),
        )
    ],
    description="Response containing a list of banks",
)


@function(name="get_banks")
@mcp.tool(name="get_banks", description="Get a list of bank names")
def get_banks(snowflake: Snowflake, request: Request) -> Response:
    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM BANKS")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return Response({"banks": [row[0] for row in rows]})
