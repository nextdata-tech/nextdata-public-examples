from contracts import adls_freshness
from models import history
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

cluster_config = {
    "autoscale": {
        "min_workers": 1,
        "max_workers": 1,
    },
    "node_type_id": "Standard_D8_v3",
    "spark_version": "15.4.x-scala2.12",
    "store_path": "/Workspace/nxd",
}

__all__ = [
    "adls_freshness",
    "history",
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
    "cluster_config",
]
