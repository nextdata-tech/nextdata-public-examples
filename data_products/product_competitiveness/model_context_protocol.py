from nxd.core.context import Snowflake
from nxd.core.yaml_schemas import DataType
from nxd.core.yaml_schemas import Field
from nxd.drivers.rpc import Request
from nxd.drivers.rpc import Response
from nxd.drivers.rpc import function
from nxd.drivers.rpc import mcp
from nxd.spec import attribute
from nxd.spec import semantic_model
from nxd.spec.data_types import decimal
from nxd.spec.data_types import int64
from nxd.spec.data_types import list
from nxd.spec.data_types import string
from nxd.spec.data_types import struct
from snowflake.connector import DictCursor
from snowflake.connector import connect


def _field(name: str | None, data_type: DataType) -> Field:
    # helper function for DataType.ComplexType which expects
    #   Field classes and not dicts or tuples
    return Field(
        data_type=data_type,
        name=name,
        description=None,
        metadata=None,
        constraints=None,
        relates_to=[],
        semantic_tags=None,
    )


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
            data_type=list(_field("banks", string())),
            description="List of bank names",
        )
    ],
    description="Response containg a list of banks",
)


@function(name="get_banks")
@mcp.tool(name="get_banks", description="Get a list of bank names")
def get_banks(
    snowflake: Snowflake,
    request: Request,
) -> Response:
    return Response({"banks": ["Westpac", "ANZ", "Macquarie"]})


get_term_deposit_rates_request = (
    semantic_model("get_term_deposit_rates_request")
    .description("Request to get a list of term deposit rates for a particular bank")
    .schema({"bank": (string(), "Name of the bank")})
)

get_term_deposit_rates_response = (
    semantic_model("get_term_deposit_rates_response")
    .description("Response to get a list of all term deposit rates across banks")
    .schema(
        {
            "term_deposits": list(
                _field(
                    "term_deposits",
                    struct(
                        [
                            _field("name", string()),
                            _field("bank", string()),
                            _field("min_amount", int64()),
                            _field("max_amount", int64()),
                            _field("min_term", int64()),
                            _field("max_term", int64()),
                            _field("monthly_rate", decimal(4, 2)),
                            _field("annual_rate", decimal(4, 2)),
                            _field("maturity_rate", decimal(4, 2)),
                        ]
                    ),
                )
            )
        }
    )
)


@function(name="get_term_deposit_rates")
@mcp.tool(name="get_term_deposit_rates", description="Get term deposit rates for a bank")
def get_term_deposit_rates(
    snowflake: Snowflake,
    request: Request,
) -> Response:
    # TODO: return appropriate error if bank not in (Westpac, ANZ, Macquarie)
    bank = request.bank
    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor(DictCursor)
    cursor.execute("SELECT * FROM TERM_DEPOSITS WHERE bank = %s", bank)
    term_deposits = cursor.fetchall()
    cursor.close()
    conn.close()
    return Response({"term_deposits": term_deposits})


get_home_loan_rates_request = (
    semantic_model("get_home_loan_rates_request")
    .description("Request to get a list of home loan rates for a particular bank")
    .schema({"bank": (string(), "Name of the bank")})
)

get_home_loan_rates_response = (
    semantic_model("get_home_loan_rates_response")
    .description("Response to get a list of all home loan rates across banks")
    .schema(
        {
            "home_loans": list(
                _field(
                    "home_loans",
                    struct(
                        [
                            _field("bank", string()),
                            _field("product", string()),
                            _field("loan_term", int64()),
                            _field("min_lvr", int64()),
                            _field("max_lvr", int64()),
                            _field("min_loan", decimal(4, 2)),
                            _field("max_loan", decimal(4, 2)),
                            _field("rate", decimal(4, 2)),
                        ]
                    ),
                )
            )
        }
    )
)


@function(name="get_home_loan_rates")
@mcp.tool(name="get_home_loan_rates", description="Get home loan rates for a bank")
def get_home_loan_rates(
    snowflake: Snowflake,
    request: Request,
) -> Response:
    # TODO: return appropriate error if bank not in (Westpac, ANZ, Macquarie)
    bank = request.bank
    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor(DictCursor)
    cursor.execute("SELECT * FROM HOME_LOAN_RATES WHERE bank = %s", bank)
    home_loans = cursor.fetchall()
    cursor.close()
    conn.close()
    return Response({"home_loans": home_loans})
