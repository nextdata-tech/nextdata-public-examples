# ruff: noqa: F403, F405
from nxd_models import *

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
            "rep_id": (string(), "Rep who performed the activity (MKTG-01 = HQ campaign)."),
            "territory_id": (string(), "Territory in which the activity occurred."),
            "activity_month": (string(), "Calendar month of the activity ('YYYY-MM')."),
            "channel": (string(), "Channel through which the activity was conducted."),
            "activity_type": (string(), "Type of engagement (Detail, Sample Drop, ...)."),
            "product_discussed": (string(), "Product or SKU discussed during the activity."),
            "duration_min": (int64(), "Duration of the activity in minutes."),
            "engagement_score": (int64(), "Engagement quality score for the activity (0-100)."),
            "response": (string(), "Account response (Positive, Neutral, Negative, No Response)."),
            "on_preferred_channel": (boolean(), "Whether the touch used the account's preferred channel."),
            "sample_dropped": (boolean(), "Whether product samples were dropped."),
            "estimated_cost_usd": (int64(), "Fully-loaded per-touch cost, USD."),
        }
    )
)

rep_territory_scorecard = (
    semantic_model(
        name="rep_territory_scorecard",
        description=(
            "Rep / territory performance scorecard including a field-vs-HQ flag (MKTG-01 / T-MKT campaign rows)."
        ),
    )
    .sampling(SamplingMethod.Random)
    .schema(
        {
            "rep_id": (string(), "Rep identifier (MKTG-01 = HQ multichannel campaign)."),
            "territory_id": (string(), "Territory identifier (T-MKT = HQ campaign)."),
            "is_hq_campaign": (boolean(), "True when the row is an HQ campaign rather than field activity."),
            "activity_count": (int64(), "Number of activities for the rep/territory."),
            "distinct_accounts": (int64(), "Number of distinct accounts touched."),
            "avg_engagement_score": (decimal(6, 2), "Mean engagement score."),
            "positive_rate": (decimal(6, 4), "Share of activities with a Positive response."),
            "total_cost_usd": (int64(), "Total estimated cost, USD."),
            "avg_cost_per_activity_usd": (decimal(12, 2), "Mean estimated cost per activity, USD."),
        }
    )
)
