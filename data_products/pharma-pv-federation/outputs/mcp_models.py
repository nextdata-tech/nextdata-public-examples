from nxd.spec import semantic_model
from nxd.spec.data_types import string

get_metadata_request = (
    semantic_model("get_metadata_request")
    .schema({
        "database": (
            string(),
            "Optional. Snowflake database holding the two PV schemas. "
            "Pass null to use the connection default.",
        ),
    })
    .description("Request live schema metadata for the two federated PV tables.")
)

get_metadata_response = (
    semantic_model("get_metadata_response")
    .schema({
        "metadata": (string(), "Table schemas, join keys, metric formula, and example query."),
        "source":   (string(), "Source of semantic definitions (information_schema / glossary)."),
    })
    .description("Live metadata for adverse_event_summary and prescription_volume.")
)

execute_federated_query_request = (
    semantic_model("execute_federated_query_request")
    .schema({
        "sql": (
            string(),
            "A complete SQL SELECT or WITH statement. Typically JOINs "
            "drug_safety_signals.adverse_event_summary with "
            "commercial_prescriptions.prescription_volume on "
            "product_id, region, and report_period.",
        ),
    })
    .description("A SQL SELECT (cross-domain PV JOIN) to run against Snowflake.")
)

execute_federated_query_response = (
    semantic_model("execute_federated_query_response")
    .schema({
        "result":    (string(), "Query results as a formatted text table."),
        "row_count": (string(), "Number of rows returned."),
    })
    .description("Results of the federated pharmacovigilance query.")
)
