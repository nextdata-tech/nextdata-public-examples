import os
import sys

from databricks import sql as dbsql  # type: ignore[reportAttributeAccessIssue]
from nxd.core.context import DatabricksRead
from nxd.core.yaml_schemas import DataType
from nxd.core.yaml_schemas import Field
from nxd.drivers.rpc import Request
from nxd.drivers.rpc import Response
from nxd.drivers.rpc import function
from nxd.drivers.rpc import mcp
from nxd.spec import SemanticModelSpec
from nxd.spec import semantic_model
from nxd.spec.data_types import float64
from nxd.spec.data_types import list
from nxd.spec.data_types import string
from nxd.spec.data_types import struct

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))


def configure_logger():
    import logging

    logger = logging.getLogger(__name__)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)
    return logger


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


@function(name="get_top_revenue")
@mcp.tool(name="get_top_revenue", description="Get top revenue companies for a given year")
def get_top_revenue(request: Request, databricks: DatabricksRead) -> Response:
    """Fetches top revenue companies from the financial statements data."""
    logger = configure_logger()
    logger.warning("Received request for get_top_revenue: %s", request)
    logger.warning("Databricks context: %s", databricks)
    year = request.get("year")

    cash_flows = databricks.full_table_name("cash_flows")
    access_token = databricks.token
    with dbsql.connect(
        server_hostname=databricks.host,
        http_path=databricks.http_path,
        access_token=access_token,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    symbol,
                    value AS revenue
                FROM {cash_flows}
                WHERE metric = 'operating_cash_flow'
                  AND YEAR(date) = {year}
                ORDER BY value DESC
                """
            )
            rows = cursor.fetchall()

    result = [{"symbol": row[0], "year": year, "revenue": row[1]} for row in rows]

    return Response({"result": result})


class TopRevenueAPI:
    @staticmethod
    def get_request_model() -> SemanticModelSpec:
        return semantic_model("top_revenue_request").schema({"year": (string(), "Year")})

    @staticmethod
    def get_response_model() -> SemanticModelSpec:
        return semantic_model("top_revenue_response").schema(
            {
                "top_companies": list(
                    _field(
                        "top_companies",
                        struct(
                            [
                                _field("symbol", string()),
                                _field("year", string()),
                                _field("revenue", float64()),
                            ]
                        ),
                    )
                )
            }
        )
