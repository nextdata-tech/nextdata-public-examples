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
            "account_type": (string(), "'Person' (HCP) or 'Organization' (HCO)."),
            "first_name": (string(), "Given name of the person account."),
            "last_name": (string(), "Family name of the person account."),
            "npi": (int64(), "National Provider Identifier (10-digit)."),
            "specialty": (string(), "Primary medical specialty of the account."),
            "state": (string(), "Two-letter US state code."),
            "prescribing_decile": (int64(), "Prescribing volume decile 1 (low) to 10 (high)."),
            "segment": (string(), "Field-force value segment (A/B/C/D)."),
            "account_value_tier": (string(), "Value tier (High, Medium, or Low)."),
            "potential_value_usd": (int64(), "Estimated addressable revenue opportunity, USD."),
            "actual_value_usd": (int64(), "Realized revenue attributed to the account, USD."),
            "preferred_channel": (string(), "Account's preferred engagement channel."),
            "email_opt_in": (boolean(), "Whether the account consented to email."),
            "territory_id": (string(), "Sales territory the account belongs to."),
            "primary_rep_id": (string(), "Rep primarily responsible for the account."),
            "status": (string(), "Lifecycle status (Active / Inactive)."),
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

channel_effectiveness = (
    semantic_model(
        name="channel_effectiveness",
        description=(
            "Per-channel effectiveness and cost-efficiency: engagement, "
            "positive-response rate, on-preferred-channel rate, and cost per "
            "positive response."
        ),
    )
    .sampling(SamplingMethod.Random)
    .schema(
        {
            "channel": (string(), "Engagement channel (F2F, Remote, Email, Phone, Conference, Virtual Event)."),
            "activity_count": (int64(), "Number of activities conducted on this channel."),
            "avg_engagement_score": (decimal(6, 2), "Mean engagement score for the channel."),
            "positive_rate": (decimal(6, 4), "Share of activities with a Positive response."),
            "on_preferred_channel_rate": (
                decimal(6, 4),
                "Share of activities that used the account's preferred channel.",
            ),
            "total_cost_usd": (int64(), "Total estimated cost across the channel, USD."),
            "cost_per_positive_usd": (
                decimal(12, 2),
                "total_cost_usd / positive responses (0 when no positives).",
            ),
        }
    )
)

monthly_trends = (
    semantic_model(
        name="monthly_trends",
        description=("Monthly activity and engagement trend, including the F2F-to-digital channel shift over time."),
    )
    .sampling(SamplingMethod.Random)
    .schema(
        {
            "activity_month": (string(), "Calendar month ('YYYY-MM')."),
            "activity_count": (int64(), "Number of activities in the month."),
            "avg_engagement_score": (decimal(6, 2), "Mean engagement score for the month."),
            "positive_rate": (decimal(6, 4), "Share of activities with a Positive response."),
            "f2f_share": (decimal(6, 4), "Share of activities on the F2F channel."),
            "digital_share": (decimal(6, 4), "Share of activities on Email / Remote / Virtual Event."),
            "total_cost_usd": (int64(), "Total estimated cost for the month, USD."),
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

