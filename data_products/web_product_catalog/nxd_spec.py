from models import catalog_products
from nxd.spec import code
from nxd.spec import custom
from nxd.spec import data_product
from nxd.spec import data_product_access
from nxd.spec import data_product_output
from nxd.spec import owner
from nxd.spec import snowflake_config
from nxd.spec import source_aligned_input
from nxd.spec import storage
from nxd.spec.conditions import scheduled
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
    "catalog_products",
    "code",
    "custom",
    "data_product",
    "data_product_access",
    "data_product_output",
    "k8s_executor_config",
    "owner",
    "snowflake_config",
    "source_aligned_input",
    "storage",
    "transform",
    "scheduled",
]
