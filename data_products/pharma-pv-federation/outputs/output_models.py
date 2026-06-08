from nxd.spec import SamplingMethod
from nxd.spec import semantic_model
from nxd.spec.data_types import int64
from nxd.spec.data_types import string

pv_registry = (
    semantic_model("pv_registry")
    .sampling(method=SamplingMethod.Head)
    .description(
        "Registry of the two federated pharmacovigilance tables. "
        "Its Snowflake output port anchors the credential context for the MCP tools."
    )
    .schema({
        "safety_table":     (string(), "Fully-qualified adverse-event summary table."),
        "commercial_table": (string(), "Fully-qualified prescription-volume table."),
        "join_keys":        (string(), "Join keys shared by both tables."),
        "safety_row_count": (int64(),  "Row count in the safety table at registration time."),
        "registered_at":    (string(), "Timestamp when this row was last refreshed."),
    })
)
