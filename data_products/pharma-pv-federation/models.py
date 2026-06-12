# ruff: noqa: F403, F405
from nxd_models import *

# This orchestrator does not own pharmacovigilance data: the adverse-event and
# prescription tables live in their own governed data products and are read at
# query time through Snowflake. pv_registry is a single, constant anchor row.
# Its only purpose is to give this data product a concrete Snowflake output
# table so the platform provisions live Snowflake credentials for it -- the MCP
# tools then borrow those credentials to run federated, cross-schema reads.
#
# Crucially, the transform that fills this row reads NO other schema and counts
# NO upstream rows, so it can never fail because a source table is empty or not
# yet visible. It is pure metadata.
pv_registry = semantic_model(
    name="pv_registry",
    description=(
        "Pharmacovigilance federation registry. A single anchor row describing "
        "which source tables this orchestrator federates and how they combine. "
        "Carries no PII and no event-level data."
    ),
).schema(
    {
        "registry_id": (
            string(),
            "Constant identifier for this federation registry ('pharma-pv-federation').",
        ),
        "safety_source": (
            string(),
            "Fully-qualified adverse-event (numerator) table that supplies event counts.",
        ),
        "commercial_source": (
            string(),
            "Fully-qualified prescription-volume (denominator) table that supplies Rx counts.",
        ),
        "join_keys": (
            string(),
            "Keys the two sources join on: product_id, region, report_period.",
        ),
        "rate_metric": (
            string(),
            "Definition of the adverse-event reporting rate per 1,000 prescriptions.",
        ),
        "built_at": (
            string(),
            "UTC timestamp text recording when this registry row was last rebuilt.",
        ),
    }
)
