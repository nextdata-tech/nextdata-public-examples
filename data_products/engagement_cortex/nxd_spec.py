"""
nxd_spec.py -- single import surface for spec.py.

Re-exports the one tool function and its request/response models from __mcp__,
the anchor model from models, and the nxd spec primitives spec.py needs. All
spec primitives come from `nxd.spec` (the same import path the deployed
pharma-pv-federation product uses).
"""

from __mcp__ import ask
from __mcp__ import ask_request
from __mcp__ import ask_response
from models import cortex_registry
from nxd.spec import code
from nxd.spec import data_product
from nxd.spec import data_product_access
from nxd.spec import data_product_output
from nxd.spec import data_product_rpc_output
from nxd.spec import owner
from nxd.spec import rpc_function
from nxd.spec import rpc_server
from nxd.spec import snowflake_config
from nxd.spec import sql
from nxd.spec import storage

__all__ = [
    # MCP tool
    "ask",
    # MCP request / response models
    "ask_request",
    "ask_response",
    # output model
    "cortex_registry",
    # spec primitives
    "code",
    "data_product",
    "data_product_access",
    "data_product_output",
    "data_product_rpc_output",
    "owner",
    "rpc_function",
    "rpc_server",
    "snowflake_config",
    "sql",
    "storage",
]
