"""
models.py -- semantic model definitions for the account-coverage data product.

These are ORDINARY nextdata semantic models, defined the standard way with
`.schema({column: (type, description)})`. There is deliberately NO separate
"metadata dictionary" here: the model objects below ARE the single source of
truth for the schema. The get_schema MCP tool reads these same objects at
runtime (via their Pydantic `.model_dump()`), so whatever you change here -- a
new column, a tweaked description, an allowed-value note -- is exactly what the
agent sees. The descriptions are intentionally rich (allowed values, business
rules, ranking hints) because that richness is what lets the agent author
correct SQL without any hardcoded example queries in the tool code.
"""

from nxd_models import SamplingMethod
from nxd_models import decimal
from nxd_models import int64
from nxd_models import semantic_model
from nxd_models import string


# ─────────────────────────────────────────────────────────────────────────────
# Upstream inputs (consumed from the crm-activity data product). Declared so the
# input expectations are explicit; not exposed as this product's own output.
# ─────────────────────────────────────────────────────────────────────────────
account = (
    semantic_model(
        name="account",
        description="Upstream crm-activity ACCOUNT table consumed by this product.",
    )
    .sampling(SamplingMethod.Random)
    .schema(
        {
            "account_id": (string(), "Unique CRM identifier for the account."),
            "account_value_tier": (string(), "Value tier (High, Medium, or Low)."),
            "segment": (string(), "Field-force value segment (A/B/C/D)."),
            "specialty": (string(), "Primary medical specialty of the account."),
            "territory_id": (string(), "Sales territory the account belongs to."),
            "potential_value_usd": (int64(), "Estimated addressable revenue opportunity, USD."),
            "actual_value_usd": (int64(), "Realized revenue attributed to the account, USD."),
        }
    )
)

activity = (
    semantic_model(
        name="activity",
        description="Upstream crm-activity ACTIVITY table consumed by this product.",
    )
    .sampling(SamplingMethod.Random)
    .schema(
        {
            "activity_id": (string(), "Unique identifier for the engagement activity."),
            "account_id": (string(), "Account the activity was logged against."),
            "channel": (string(), "Channel through which the activity was conducted."),
            "engagement_score": (int64(), "Engagement quality score for the activity (0-100)."),
            "response": (string(), "Account response: Positive, Neutral, Negative, No Response."),
            "estimated_cost_usd": (int64(), "Fully-loaded per-touch cost, USD."),
        }
    )
)


# ─────────────────────────────────────────────────────────────────────────────
# This product's output model. get_schema serves these columns + descriptions.
# ─────────────────────────────────────────────────────────────────────────────
account_coverage = (
    semantic_model(
        name="account_coverage",
        description=(
            "Per-account coverage and value-gap analysis: realized vs. potential "
            "value, touch volume, cost, engagement, and a coverage classification "
            "flagging under-served high-value and over-served low-value accounts."
        ),
    )
    .sampling(SamplingMethod.Random)
    .schema(
        {
            "account_id": (
                string(),
                "Unique CRM account identifier. Joins to crm-activity account.account_id.",
            ),
            "account_value_tier": (
                string(),
                "Strategic value tier of the account. Allowed values: 'High', 'Medium', 'Low'.",
            ),
            "segment": (
                string(),
                "Field-force segment: 'A', 'B', 'C', 'D'. Segment A = highest strategic "
                "priority; D = lowest.",
            ),
            "specialty": (
                string(),
                "Primary medical specialty (e.g. 'Cardiology', 'Oncology', 'Primary Care', "
                "'Neurology').",
            ),
            "territory_id": (
                string(),
                "Sales territory the account belongs to (e.g. 'T-01', 'T-02'). NOTE: always "
                "exclude territory_id = 'T-MKT' from field-rep analysis -- it is a marketing "
                "territory, not a field sales territory.",
            ),
            "potential_value_usd": (
                int64(),
                "Total estimated addressable revenue opportunity for this account, USD.",
            ),
            "actual_value_usd": (
                int64(),
                "Realized revenue attributed to this account, USD.",
            ),
            "value_gap_usd": (
                int64(),
                "Unrealized revenue opportunity: potential_value_usd minus actual_value_usd. "
                "Higher = greater upside. Use for prioritisation and ranking queries.",
            ),
            "realization_ratio": (
                decimal(6, 4),
                "actual_value_usd / potential_value_usd. Range 0-1 (returns 0 when potential "
                "= 0). Multiply by 100 for percentage display: ROUND(realization_ratio * 100, 1).",
            ),
            "touch_count": (
                int64(),
                "Total number of field activities logged against this account.",
            ),
            "total_cost_usd": (
                int64(),
                "Total estimated fully-loaded cost of all field activities for this account, USD.",
            ),
            "avg_engagement_score": (
                decimal(6, 2),
                "Mean engagement quality score across all the account's activities. Range "
                "0-100. Higher = stronger engagement quality.",
            ),
            "positive_rate": (
                decimal(6, 4),
                "Fraction of the account's activities that received a Positive response. Range "
                "0-1. Multiply by 100 for percentage display.",
            ),
            "coverage_flag": (
                string(),
                "Coverage classification derived from tier, value, and activity patterns. "
                "Allowed values: 'Under-served high-value' | 'Over-served low-value' | "
                "'Well-served high-value' | 'Adequate'.",
            ),
            "account_profile_text": (
                string(),
                "Auto-generated natural language profile combining all account attributes. "
                "Indexed by the ACCOUNT_COVERAGE_SEARCH Cortex Search service for semantic "
                "search. Do not use this column in SQL WHERE clauses.",
            ),
        }
    )
)
