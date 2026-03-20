from models import dividends
from nxd.spec import ScheduleTrigger
from nxd.spec import SupportedFormat
from nxd.spec import adls_config
from nxd.spec import code
from nxd.spec import data_product
from nxd.spec import data_product_access
from nxd.spec import data_product_output
from nxd.spec import owner
from nxd.spec import storage
from transform import transform

k8s_executor_config = {
    "pod_cleanup_delay_secs": 3600,
    "startup_timeout_secs": 600,
    "resources": {
        "requests": {"memory": "768Mi", "cpu": "100m"},
        "limits": {"memory": "1500Mi", "cpu": "500m"},
    },
}

__all__ = [
    "dividends",
    "ScheduleTrigger",
    "SupportedFormat",
    "adls_config",
    "code",
    "data_product",
    "data_product_access",
    "data_product_output",
    "owner",
    "storage",
    "transform",
    "k8s_executor_config",
]
