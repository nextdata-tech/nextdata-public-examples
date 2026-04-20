from expectations import adls_atleast_one_record
from model_context_protocol import get_banks
from model_context_protocol import get_banks_request
from model_context_protocol import get_banks_response
from model_context_protocol import get_home_loan_rates
from model_context_protocol import get_home_loan_rates_request
from model_context_protocol import get_home_loan_rates_response
from model_context_protocol import get_term_deposit_rates
from model_context_protocol import get_term_deposit_rates_request
from model_context_protocol import get_term_deposit_rates_response
from models import home_loan_rates
from models import term_deposits
from models import westpac_home_loans
from nxd.spec import SupportedFormat
from nxd.spec import code
from nxd.spec import custom
from nxd.spec import data_product
from nxd.spec import data_product_access
from nxd.spec import data_product_input
from nxd.spec import data_product_output
from nxd.spec import data_product_rpc_output
from nxd.spec import owner
from nxd.spec import rpc_function
from nxd.spec import rpc_server
from nxd.spec import snowflake_config
from nxd.spec import storage
from transform import transform

from contracts import snowflake_atleast_one_record

k8s_executor_config = {
    "pod_cleanup_delay_secs": 3600,
    "startup_timeout_secs": 600,
    "resources": {
        "requests": {"memory": "768Mi", "cpu": "100m"},
        "limits": {"memory": "1500Mi", "cpu": "500m"},
    },
}

__all__ = [
    "term_deposits",
    "home_loan_rates",
    "westpac_home_loans",
    "SupportedFormat",
    "code",
    "custom",
    "data_product",
    "data_product_access",
    "data_product_input",
    "data_product_output",
    "data_product_rpc_output",
    "owner",
    "rpc_function",
    "rpc_server",
    "snowflake_config",
    "storage",
    "transform",
    "snowflake_atleast_one_record",
    "adls_atleast_one_record",
    "get_banks",
    "get_banks_request",
    "get_banks_response",
    "get_home_loan_rates",
    "get_home_loan_rates_request",
    "get_home_loan_rates_response",
    "get_term_deposit_rates",
    "get_term_deposit_rates_request",
    "get_term_deposit_rates_response",
    "k8s_executor_config",
]
