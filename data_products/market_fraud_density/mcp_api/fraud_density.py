"""
RPC / MCP API functions for the market-fraud-density data product.

Exposes two queryable endpoints:
  • get_all_fraud_stats    – full ranked list of all market categories
  • get_market_fraud_stats – stats for one specific market category

Consumable by Power BI (HTTP REST / MCP connector) and AI agentic applications.
Data is derived by running the aggregation logic on the bundled source CSV
(or the Kaggle API if credentials are available).
"""

import os
import sys

from nxd.drivers.rpc import Request
from nxd.drivers.rpc import Response
from nxd.drivers.rpc import function
from nxd.drivers.rpc import mcp
from nxd.spec import SemanticModelSpec
from nxd.spec import semantic_model
from nxd.spec.data_types import float64
from nxd.spec.data_types import int64
from nxd.spec.data_types import string

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from transform import aggregate_fraud_density
from transform import read_source_data


def _get_rows():
    """Run aggregation and return list of dicts for all market categories."""
    df_raw = read_source_data()
    df_agg = aggregate_fraud_density(df_raw)
    return df_agg.to_dict(orient="records")


# Endpoint 1: all market categories


@function(name="all_fraud_stats")
@mcp.tool(
    name="all_fraud_stats",
    description=(
        "Returns a ranked list of ALL merchant market categories with their "
        "transaction volume and fraud rate. Use this to compare fraud density "
        "across the entire market landscape."
    ),
)
def all_fraud_stats(request: Request) -> Response:
    rows = _get_rows()
    return Response(
        {
            "total_categories": len(rows),
            "market_categories": rows,
        }
    )


# Endpoint 2: single market category


@function(name="mkt_fraud_stats")
@mcp.tool(
    name="mkt_fraud_stats",
    description=(
        "Returns fraud density statistics for a specific merchant market category "
        "(e.g. 'transportation', 'food', 'hotel'). "
        "Use this to retrieve the relative risk for a single market."
    ),
)
def mkt_fraud_stats(request: Request) -> Response:
    import re

    raw_input = str(request.get("market_type", "")).strip().strip("'\"").lower()

    normalised = re.sub(r"^es_", "", raw_input)

    rows = _get_rows()
    match = next(
        (r for r in rows if str(r.get("market_type", "")).lower() == normalised),
        None,
    )

    if match is None:
        available = sorted(str(r.get("market_type", "")) for r in rows)
        return Response(
            {
                "market_type": raw_input,
                "transaction_count": 0,
                "fraud_event_count": 0,
                "fraud_rate_pct": -1.0,
                "error": f"Market type '{raw_input}' not found. Available (normalised): {available}",
            }
        )

    return Response(match)


# Request / Response model contracts
class FraudDensityAPI:
    @staticmethod
    def get_all_request_model() -> SemanticModelSpec:
        return semantic_model("fraud_density_all_request").schema({})

    @staticmethod
    def get_all_response_model() -> SemanticModelSpec:
        return semantic_model("fraud_density_all_response").schema(
            {
                "total_categories": (
                    int64(),
                    "Number of distinct market categories returned",
                ),
            }
        )

    @staticmethod
    def get_stats_request_model() -> SemanticModelSpec:
        return semantic_model("fraud_density_stats_request").schema(
            {
                "market_type": (
                    string(),
                    "Normalized merchant category name (e.g. 'transportation')",
                ),
            }
        )

    @staticmethod
    def get_stats_response_model() -> SemanticModelSpec:
        return semantic_model("fraud_density_stats_response").schema(
            {
                "market_type": (
                    string(),
                    "Merchant category (empty string if not found)",
                ),
                "transaction_count": (int64(), "Total transactions (0 if not found)"),
                "fraud_event_count": (int64(), "Total fraud events (0 if not found)"),
                "fraud_rate_pct": (float64(), "Fraud rate % (-1.0 means not found)"),
            }
        )
