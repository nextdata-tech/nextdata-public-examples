from mcp_api.fraud_density import FraudDensityAPI
from mcp_api.fraud_density import get_all_fraud_stats
from mcp_api.fraud_density import get_market_fraud_stats
from models import banksim_transactions_model
from models import fraud_density_model
from nxd.spec import ScheduleTrigger
from nxd.spec import SupportedFormat
from nxd.spec import code
from nxd.spec import custom
from nxd.spec import data_product
from nxd.spec import data_product_access
from nxd.spec import data_product_output
from nxd.spec import data_product_rpc_output
from nxd.spec import owner
from nxd.spec import rpc_function
from nxd.spec import rpc_server
from nxd.spec import s3_config
from nxd.spec import storage
from transform import transform

from contracts.banksim_transactions_quality import check_banksim_transactions_quality
from contracts.fraud_density_quality import check_fraud_density_quality

k8s_executor_config = {
    "pod_cleanup_delay_secs": 3600,
    "startup_timeout_secs": 600,
    "resources": {
        "requests": {"memory": "768Mi", "cpu": "100m"},
        "limits": {"memory": "1500Mi", "cpu": "500m"},
    },
}

__all__ = [
    "banksim_transactions_model",
    "fraud_density_model",
    "ScheduleTrigger",
    "SupportedFormat",
    "code",
    "custom",
    "data_product",
    "data_product_access",
    "data_product_output",
    "data_product_rpc_output",
    "owner",
    "rpc_function",
    "rpc_server",
    "s3_config",
    "storage",
    "transform",
    "k8s_executor_config",
    "get_market_fraud_stats",
    "get_all_fraud_stats",
    "FraudDensityAPI",
    "check_banksim_transactions_quality",
    "check_fraud_density_quality",
]
