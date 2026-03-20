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
from nxd.spec import owner
from nxd.spec import snowflake_config
from nxd.spec import storage
from transform import transform

from contracts import snowflake_atleast_one_record

k8s_executor_config = {
    "pod_cleanup_delay_secs": 3600,
    "startup_timeout_secs": 600,
    "resources": {
        "requests": {"memory": "768Mi", "cpu": "100m"},
        "limits": {"memory": "1024Mi", "cpu": "500m"},
    },
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
    "snowflake_config",
    "storage",
    "transform",
    "expect_data_from_all_banks",
    "snowflake_atleast_one_record",
    "k8s_executor_config",
]
