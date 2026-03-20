# Re-export MCP functions for server discovery
from mcp_api.revenue import get_revenue
from mcp_api.top_revenue import get_top_revenue

__all__ = ["get_revenue", "get_top_revenue"]
