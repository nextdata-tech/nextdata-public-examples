"""Shim re-exporting the nxd symbols `spec.py` uses via `from nxd_spec import *`.

Pulls in the project's own models and `transform` function so they're
available at spec-evaluation time, then re-exports every spec-builder
name through ``__all__``.
"""

import api_source_freshness
from __mcp__ import search_jira_issues
from models import jira_issue
from models import jira_issue_embeddings
from models import search_request
from models import search_response
from nxd.spec import code
from nxd.spec import custom
from nxd.spec import data_product
from nxd.spec import data_product_access
from nxd.spec import data_product_output
from nxd.spec import data_product_rpc_output
from nxd.spec import owner
from nxd.spec import pg_vector_config
from nxd.spec import rpc_function
from nxd.spec import rpc_server
from nxd.spec import source_aligned_input
from nxd.spec import storage
from nxd.spec.conditions import scheduled
from transform import transform

__all__ = [
    "api_source_freshness",
    "code",
    "custom",
    "data_product",
    "data_product_access",
    "data_product_output",
    "data_product_rpc_output",
    "jira_issue",
    "jira_issue_embeddings",
    "owner",
    "pg_vector_config",
    "rpc_function",
    "rpc_server",
    "scheduled",
    "search_jira_issues",
    "search_request",
    "search_response",
    "source_aligned_input",
    "storage",
    "transform",
]
