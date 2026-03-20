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
from nxd.spec import snowflake_config
from nxd.spec import storage
from transform import transform

k8s_executor_config = {
    "pod_cleanup_delay_secs": 3600,
    "startup_timeout_secs": 600,
    "resources": {
        "requests": {"memory": "768Mi", "cpu": "100m"},
        "limits": {"memory": "768Mi", "cpu": "500m"},
    },
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
    "snowflake_config",
    "storage",
    "code",
    "k8s_executor_config",
]
