from contracts import databricks_atleast_one_record
from expectations import expect_data_from_all_banks
from models import home_loan_rates
from models import term_deposits
from nxd.spec import ScheduleTrigger
from nxd.spec import code
from nxd.spec import custom
from nxd.spec import data_product
from nxd.spec import data_product_access
from nxd.spec import data_product_input
from nxd.spec import data_product_output
from nxd.spec import databricks_config
from nxd.spec import owner
from nxd.spec import storage
from transform import transform

cluster_config = {
    "autoscale": {"min_workers": 1, "max_workers": 1},
    "spark_version": "17.3.x-scala2.13",
    "store_path": "/Workspace/nxd",
    "share_cluster": True,
}

__all__ = [
    "home_loan_rates",
    "term_deposits",
    "ScheduleTrigger",
    "code",
    "custom",
    "data_product",
    "data_product_access",
    "data_product_input",
    "data_product_output",
    "owner",
    "databricks_config",
    "storage",
    "transform",
    "expect_data_from_all_banks",
    "databricks_atleast_one_record",
    "cluster_config",
]
