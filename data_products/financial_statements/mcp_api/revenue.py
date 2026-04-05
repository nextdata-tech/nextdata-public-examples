import os
import sys

from databricks import sql as dbsql  # type: ignore[reportAttributeAccessIssue]
from nxd.core.context import DatabricksRead
from nxd.drivers.rpc import Request
from nxd.drivers.rpc import Response
from nxd.drivers.rpc import function
from nxd.drivers.rpc import mcp
from nxd.spec import SemanticModelSpec
from nxd.spec import semantic_model
from nxd.spec.data_types import float64
from nxd.spec.data_types import string

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


@function(name="get_revenue")
@mcp.tool(name="get_revenue", description="Get revenue data for a given company")
def get_revenue(request: Request, databricks: DatabricksRead) -> Response:
    """Fetches revenue data for a given company."""
    logger = configure_logger()
    logger.warning("Received request for revenue data: %s", request)
    logger.warning("Databricks context: %s", databricks)
    company_id = request.get("id")
    year = request.get("year")

    cash_flows = databricks.full_table_name("cash_flows")
    with dbsql.connect(
        server_hostname=databricks.host,
        http_path=databricks.http_path,
        access_token=databricks.token,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    symbol,
                    value AS revenue
                FROM {cash_flows}
                WHERE metric = 'operating_cash_flow'
                  AND symbol ILIKE '%{company_id}%'
                  AND YEAR(date) = {year}
                """
            )
            row = cursor.fetchone()

    if row is None:
        return Response({"symbol": company_id, "year": year, "revenue": None})

    return Response({"symbol": row[0], "year": year, "revenue": row[1]})


class RevenueAPI:
    @staticmethod
    def get_request_model() -> SemanticModelSpec:
        return semantic_model("revenue_request").schema(
            {"id": (string(), "Stock ticker symbol (e.g. WBC.AX)"), "year": (string(), "Year")}
        )

    @staticmethod
    def get_response_model() -> SemanticModelSpec:
        return semantic_model("revenue_response").schema(
            {
                "symbol": (string(), "Stock ticker symbol"),
                "year": (string(), "Year"),
                "revenue": (float64(), "Revenue Amount"),
            }
        )
