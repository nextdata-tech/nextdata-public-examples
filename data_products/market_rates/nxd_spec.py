from contracts import adls_freshness
from contracts import api_atleast_one_record
from models import anz_products
from models import macquarie_home_loans
from models import macquarie_term_deposits
from models import westpac_home_loans
from models import westpac_term_deposits
from nxd.spec import ScheduleTrigger
from nxd.spec import SupportedFormat
from nxd.spec import adls_config
from nxd.spec import code
from nxd.spec import custom
from nxd.spec import data_product
from nxd.spec import data_product_access
from nxd.spec import data_product_output
from nxd.spec import owner
from nxd.spec import source_aligned_input
from nxd.spec import storage
from transform import transform

k8s_executor_config = {
    "pod_cleanup_delay_secs": 3600,
    "startup_timeout_secs": 600,
    "resources": {
        "requests": {"memory": "768Mi", "cpu": "100m"},
        "limits": {"memory": "1524Mi", "cpu": "500m"},
    },
}

__all__ = [
    "adls_freshness",
    "api_atleast_one_record",
    "anz_products",
    "custom",
    "macquarie_home_loans",
    "macquarie_term_deposits",
    "westpac_home_loans",
    "westpac_term_deposits",
    "ScheduleTrigger",
    "SupportedFormat",
    "adls_config",
    "code",
    "data_product",
    "data_product_access",
    "data_product_output",
    "owner",
    "source_aligned_input",
    "storage",
    "transform",
    "k8s_executor_config",
]
