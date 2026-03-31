from __mcp__ import get_banks
from __mcp__ import get_banks_request
from __mcp__ import get_banks_response
from models import banks
from nxd.spec import code
from nxd.spec import data_product
from nxd.spec import data_product_output
from nxd.spec import data_product_rpc_output
from nxd.spec import rpc_function
from nxd.spec import rpc_server
from nxd.spec import databricks_config
from nxd.spec import storage
from transform import transform

cluster_config = {
    "autoscale": {"min_workers": 1, "max_workers": 1},
    "spark_version": "17.3.x-scala2.13",
    "store_path": "/Workspace/nxd",
    "share_cluster": True,
}

__all__ = [
    "get_banks",
    "get_banks_request",
    "get_banks_response",
    "banks",
    "transform",
    "data_product",
    "data_product_output",
    "data_product_rpc_output",
    "rpc_function",
    "rpc_server",
    "databricks_config",
    "storage",
    "code",
    "cluster_config",
]
