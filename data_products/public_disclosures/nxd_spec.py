from models import disclosures
from nxd.spec import ScheduleTrigger
from nxd.spec import SupportedFormat
from nxd.spec import adls_config
from nxd.spec import code
from nxd.spec import custom
from nxd.spec import data_product
from nxd.spec import data_product_access
from nxd.spec import data_product_output
from nxd.spec import owner
from nxd.spec import storage
from transform import transform

from contracts import adls_freshness

k8s_executor_config = {
    "pod_cleanup_delay_secs": 86400,
    "resources": {
        "requests": {"memory": "8Gi", "cpu": "2000m"},
        "limits": {"memory": "8Gi", "cpu": "2000m"},
    },
}

__all__ = [
    "adls_freshness",
    "disclosures",
    "custom",
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
