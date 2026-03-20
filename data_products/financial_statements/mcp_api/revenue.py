import os
import sys

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


@function(name="get_revenue")
@mcp.tool(name="get_revenue", description="Get revenue data for a given company")
def get_revenue(request: Request) -> Response:
    """Fetches revenue data for a given company."""
    company_id = request.get("id")
    year = request.get("year")

    # Fetch static revenue data for the company
    result = {
        "id": company_id,
        "company": "Example Corp",
        "year": year,
        "revenue": 1500000.00,
    }

    return Response(result)


class RevenueAPI:
    @staticmethod
    def get_request_model() -> SemanticModelSpec:
        return semantic_model("revenue_request").schema({"id": (string(), "Company ID"), "year": (string(), "Year")})

    @staticmethod
    def get_response_model() -> SemanticModelSpec:
        return semantic_model("revenue_response").schema(
            {
                "id": (string(), "Company ID"),
                "company": (string(), "Company Name"),
                "year": (string(), "Year"),
                "revenue": (float64(), "Revenue Amount"),
            }
        )
