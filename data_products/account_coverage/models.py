# ruff: noqa: F403, F405
from nxd_models import *

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
            "response": (string(), "Account response (Positive, Neutral, Negative, No Response)."),
            "estimated_cost_usd": (int64(), "Fully-loaded per-touch cost, USD."),
        }
    )
)

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
            "account_id": (string(), "Account identifier (joins to crm-activity account.account_id)."),
            "account_value_tier": (string(), "Value tier of the account (High, Medium, Low)."),
            "segment": (string(), "Current field-force segment (A/B/C/D)."),
            "specialty": (string(), "Primary medical specialty."),
            "territory_id": (string(), "Territory the account belongs to."),
            "potential_value_usd": (int64(), "Estimated addressable revenue opportunity, USD."),
            "actual_value_usd": (int64(), "Realized revenue attributed to the account, USD."),
            "value_gap_usd": (int64(), "potential_value_usd - actual_value_usd (addressable upside)."),
            "realization_ratio": (decimal(6, 4), "actual_value_usd / potential_value_usd (0 when no potential)."),
            "touch_count": (int64(), "Number of activities logged against the account."),
            "total_cost_usd": (int64(), "Total estimated cost of all activities for the account, USD."),
            "avg_engagement_score": (decimal(6, 2), "Mean engagement score across the account's activities."),
            "positive_rate": (decimal(6, 4), "Share of the account's activities with a Positive response."),
            "coverage_flag": (
                string(),
                "Classification: 'Under-served high-value', 'Over-served low-value', "
                "'Well-served high-value', or 'Adequate'.",
            ),
        }
    )
)
