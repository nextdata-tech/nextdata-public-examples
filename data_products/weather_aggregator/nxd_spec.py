from models import unified_weather_model
from nxd.spec import code
from nxd.spec import data_product
from nxd.spec import data_product_access
from nxd.spec import data_product_input
from nxd.spec import data_product_output
from nxd.spec import owner
from nxd.spec import snowflake_config
from nxd.spec import storage
from nxd.spec.conditions import any_of
from nxd.spec.conditions import updated
from transform import transform

k8s_executor_config = {
    "pod_cleanup_delay_secs": 3600,
    "startup_timeout_secs": 600,
    "resources": {
        "requests": {"memory": "256Mi", "cpu": "100m"},
        "limits": {"memory": "512Mi", "cpu": "500m"},
    },
}

__all__ = [
    "any_of",
    "code",
    "data_product",
    "data_product_access",
    "data_product_input",
    "data_product_output",
    "k8s_executor_config",
    "owner",
    "snowflake_config",
    "storage",
    "transform",
    "unified_weather_model",
    "updated",
]
