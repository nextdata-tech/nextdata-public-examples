import os
import sys

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
def get_top_revenue(request: Request) -> Response:
    """Fetches top revenue companies from the financial statements data."""
    year = request.get("year")

    result = [
        {"id": "ANZ.AX", "company": "ANZ Group Holdings Limited", "year": year, "revenue": 22307000000.00},
        {"id": "WBC.AX", "company": "Westpac Banking Corporation", "year": year, "revenue": 21587000000.00},
        {"id": "MQG.AX", "company": "Macquarie Group Limited", "year": year, "revenue": 6790000000.00},
    ]

    return Response({"result": result})


class TopRevenueAPI:
    @staticmethod
    def get_request_model() -> SemanticModelSpec:
        return semantic_model("top_revenue_request").schema({"year": (string(), "Year")})

    @staticmethod
    def get_response_model() -> SemanticModelSpec:
        return semantic_model("top_revenue_response").schema(
            # {
            #     "id": (string(), "Company ID"),
            #     "company": (string(), "Company Name"),
            #     "year": (string(), "Year"),
            #     "revenue": (float64(), "Revenue Amount"),
            # }
            {
                "top_companies": list(
                    _field(
                        "top_companies",
                        struct(
                            [
                                _field("id", string()),
                                _field("company", string()),
                                _field("year", string()),
                                _field("revenue", float64()),
                            ]
                        ),
                    )
                )
            }
        )
