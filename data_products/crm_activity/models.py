# ruff: noqa: F403, F405
from nxd_models import *

# ---------------------------------------------------------------------------
# account — BASE model, one row per CRM account (grain: account_id).
#
# Fields carry ONLY primary_key / dimension / join roles — a base field can
# never be a metric. The realized/potential revenue columns carry no role;
# they are aggregated only through the account_metrics semantic view below.
# ---------------------------------------------------------------------------

account = (
    semantic_model(
        name="account",
        description=(
            "CRM accounts representing healthcare professionals (individuals) "
            "and healthcare organizations targeted by the field sales force, "
            "including their location, specialty, value tiering, and territory "
            "assignment."
        ),
    )
    .sampling(SamplingMethod.Random)
    .fields(
        {
            "account_id": field(
                string(),
                primary_key(),
                description="Unique CRM identifier for the account (e.g. '0013x000001').",
            ),
            "account_type": field(
                string(),
                dimension(
                    name="account_type",
                    description="Whether the account is an individual 'Person' or an 'Organization'.",
                ),
                description="Whether the account is an individual 'Person' or an 'Organization'.",
            ),
            "first_name": field(
                string(),
                description="Given name of the person account; blank for organization accounts.",
            ),
            "last_name": field(
                string(),
                description="Family name of the person account; blank for organization accounts.",
            ),
            "hco_name": field(
                string(),
                description=(
                    "Healthcare organization name; populated for organization accounts, blank for person accounts."
                ),
            ),
            "npi": field(
                int64(),
                dimension(
                    name="npi",
                    description="National Provider Identifier, the unique 10-digit healthcare provider number.",
                    pii=True,
                ),
                description="National Provider Identifier, the unique 10-digit healthcare provider number.",
            ),
            "specialty": field(
                string(),
                dimension(
                    name="specialty",
                    description="Primary medical specialty of the account (e.g. Cardiology, Oncology, Primary Care).",
                ),
                description="Primary medical specialty of the account (e.g. Cardiology, Oncology, Primary Care).",
            ),
            "city": field(
                string(),
                dimension(name="city", description="City where the account is located."),
                description="City where the account is located.",
            ),
            "state": field(
                string(),
                dimension(
                    name="state",
                    description="Two-letter US state code where the account is located.",
                ),
                description="Two-letter US state code where the account is located.",
            ),
            "prescribing_decile": field(
                int64(),
                dimension(
                    name="prescribing_decile",
                    description="Prescribing volume decile from 1 (lowest) to 10 (highest) relative to peers.",
                ),
                description="Prescribing volume decile from 1 (lowest) to 10 (highest) relative to peers.",
            ),
            "segment": field(
                string(),
                dimension(
                    name="segment",
                    description="Strategic value segment of the account (A, B, or C).",
                ),
                description="Strategic value segment of the account (A, B, or C).",
            ),
            "account_value_tier": field(
                string(),
                dimension(
                    name="account_value_tier",
                    description="Categorical value tier of the account (High, Medium, or Low).",
                ),
                description="Categorical value tier of the account (High, Medium, or Low).",
            ),
            "potential_value_usd": field(
                int64(),
                description="Estimated total addressable revenue opportunity for the account, in USD.",
            ),
            "actual_value_usd": field(
                int64(),
                description="Realized revenue attributed to the account to date, in USD.",
            ),
            "preferred_channel": field(
                string(),
                dimension(
                    name="preferred_channel",
                    description="Account's preferred engagement channel (e.g. F2F, Remote, Email, Phone, Conference).",
                ),
                description="Account's preferred engagement channel (e.g. F2F, Remote, Email, Phone, Conference).",
            ),
            "email_opt_in": field(
                boolean(),
                description="Whether the account has consented to receive marketing/email communications.",
            ),
            "target_flag": field(
                string(),
                dimension(
                    name="target_flag",
                    description="Whether the account is on the active call plan / target list ('Y' or 'N').",
                ),
                description="Whether the account is on the active call plan / target list ('Y' or 'N').",
            ),
            "territory_id": field(
                string(),
                dimension(
                    name="territory_id",
                    description="Identifier of the sales territory the account belongs to (e.g. 'T-01').",
                ),
                description="Identifier of the sales territory the account belongs to (e.g. 'T-01').",
            ),
            "primary_rep_id": field(
                string(),
                dimension(
                    name="primary_rep_id",
                    description=(
                        "Identifier of the sales representative primarily responsible for the account (e.g. 'R-001')."
                    ),
                ),
                description=(
                    "Identifier of the sales representative primarily responsible for the account (e.g. 'R-001')."
                ),
            ),
            "status": field(
                string(),
                dimension(
                    name="status",
                    description="Lifecycle status of the account (e.g. Active, Inactive).",
                ),
                description="Lifecycle status of the account (e.g. Active, Inactive).",
            ),
        }
    )
)

# ---------------------------------------------------------------------------
# activity — BASE model, one row per field-sales activity (grain: activity_id).
#
# MANY activities per account: account_id carries an N:1 join to `account`, so
# activity-grain queries can slice by the account's region dimensions
# (territory_id, state, ...). activity_month is the date/quarter-filterable
# dimension. Fields carry ONLY primary_key / dimension / join roles.
# ---------------------------------------------------------------------------

activity = (
    semantic_model(
        name="activity",
        description=(
            "Field sales engagement activities (calls, details, sample drops, "
            "follow-ups, and inquiries) logged against CRM accounts, capturing "
            "channel, product discussed, engagement outcome, cost, and the "
            "recommended next best action."
        ),
    )
    .sampling(SamplingMethod.Random)
    .fields(
        {
            "activity_id": field(
                string(),
                primary_key(),
                description="Unique identifier for the engagement activity (e.g. 'a0G000001').",
            ),
            "account_id": field(
                string(),
                join(
                    to="account",
                    to_column="account_id",
                    cardinality=Cardinality.MANY_TO_ONE,
                ),
                description=("Identifier of the account the activity was logged against; joins to account.account_id."),
            ),
            "rep_id": field(
                string(),
                dimension(
                    name="rep_id",
                    description="Identifier of the sales representative who performed the activity (e.g. 'R-001').",
                ),
                description="Identifier of the sales representative who performed the activity (e.g. 'R-001').",
            ),
            "territory_id": field(
                string(),
                dimension(
                    name="territory_id",
                    description="Identifier of the sales territory in which the activity occurred (e.g. 'T-01').",
                ),
                description="Identifier of the sales territory in which the activity occurred (e.g. 'T-01').",
            ),
            "activity_datetime": field(
                timestamp(unit=DurationUnit.Nanoseconds),
                description="Date and time the activity took place.",
            ),
            "activity_month": field(
                string(),
                dimension(
                    name="activity_month",
                    description="Calendar month of the activity in 'YYYY-MM' format, derived from activity_datetime.",
                ),
                description="Calendar month of the activity in 'YYYY-MM' format, derived from activity_datetime.",
            ),
            "channel": field(
                string(),
                dimension(
                    name="channel",
                    description="Channel through which the activity was conducted (e.g. F2F, Remote, Email, Phone).",
                ),
                description="Channel through which the activity was conducted (e.g. F2F, Remote, Email, Phone).",
            ),
            "activity_type": field(
                string(),
                dimension(
                    name="activity_type",
                    description="Type of engagement (e.g. Detail, Sample Drop, Follow-up, Medical Inquiry).",
                ),
                description="Type of engagement (e.g. Detail, Sample Drop, Follow-up, Medical Inquiry).",
            ),
            "product_discussed": field(
                string(),
                dimension(
                    name="product_discussed",
                    description="Product or SKU discussed during the activity (e.g. 'Cardivex 10mg', 'Neurolyn').",
                ),
                description="Product or SKU discussed during the activity (e.g. 'Cardivex 10mg', 'Neurolyn').",
            ),
            "detail_priority": field(
                int64(),
                description=(
                    "Priority ranking of the product detail during the activity (1 = primary, higher = lower priority)."
                ),
            ),
            "duration_min": field(
                int64(),
                description="Duration of the activity in minutes.",
            ),
            "engagement_score": field(
                int64(),
                description="Computed engagement quality score for the activity (0-100).",
            ),
            "response": field(
                string(),
                dimension(
                    name="response",
                    description="Account's response or sentiment to the activity (Positive, Neutral, or Negative).",
                ),
                description="Account's response or sentiment to the activity (Positive, Neutral, or Negative).",
            ),
            "on_preferred_channel": field(
                boolean(),
                description="Whether the activity was conducted via the account's preferred channel.",
            ),
            "sample_dropped": field(
                boolean(),
                description="Whether product samples were dropped during the activity.",
            ),
            "sample_quantity": field(
                int64(),
                description="Quantity of product samples left with the account; 0 when no samples were dropped.",
            ),
            "estimated_cost_usd": field(
                int64(),
                description="Estimated cost of conducting the activity, in USD.",
            ),
            "next_best_action": field(
                string(),
                dimension(
                    name="next_best_action",
                    description="Recommended follow-up action for the account (e.g. 'Schedule follow-up detail').",
                ),
                description="Recommended follow-up action for the account (e.g. 'Schedule follow-up detail').",
            ),
            "follow_up_required": field(
                boolean(),
                description="Whether a follow-up is required as a result of this activity.",
            ),
        }
    )
)

# ---------------------------------------------------------------------------
# account_metrics — a semantic_view OVER account. Consume-time only: never
# promised, never produced/written by the transform. Carries the revenue
# metrics an agent asks for by name, sliceable by account's region dimensions
# (territory_id, state, ...).
# ---------------------------------------------------------------------------

account_metrics = (
    semantic_view("account_metrics", account)
    .description("Governed revenue and value metrics over the account model.")
    .fields(
        {
            "TOTAL_REVENUE": metric_field(
                int64(),
                metric(
                    Agg.SUM,
                    of=account.field("actual_value_usd"),
                    description="Total realized revenue attributed to accounts, in USD.",
                ),
            ),
            "TOTAL_POTENTIAL_VALUE": metric_field(
                int64(),
                metric(
                    Agg.SUM,
                    of=account.field("potential_value_usd"),
                    description="Total addressable revenue opportunity across accounts, in USD.",
                ),
            ),
            # Bare COUNT(*) row-count: point at the base model's "*" pseudo-column
            # so it renders COUNT(*). The metric name is the field key.
            "ACCOUNT_COUNT": metric_field(
                int64(),
                metric(
                    Agg.COUNT,
                    of=account.field("*"),
                    description="Total number of accounts.",
                ),
            ),
        }
    )
)

# ---------------------------------------------------------------------------
# activity_metrics — a semantic_view OVER activity. Consume-time only. Its
# metrics are sliceable by activity's own dimensions (activity_month, channel,
# ...) and, via the N:1 join to account, by the account's region dimensions.
# ---------------------------------------------------------------------------

activity_metrics = (
    semantic_view("activity_metrics", activity)
    .description("Governed engagement metrics over the activity model.")
    .fields(
        {
            "ACTIVITY_COUNT": metric_field(
                int64(),
                metric(
                    Agg.COUNT,
                    of=activity.field("*"),
                    description="Total number of field-sales activities.",
                ),
            ),
            "TOTAL_COST": metric_field(
                int64(),
                metric(
                    Agg.SUM,
                    of=activity.field("estimated_cost_usd"),
                    description="Total estimated cost of conducting activities, in USD.",
                ),
            ),
            "AVG_ENGAGEMENT_SCORE": metric_field(
                int64(),
                metric(
                    Agg.AVG,
                    of=activity.field("engagement_score"),
                    description="Mean engagement quality score across activities (0-100).",
                ),
            ),
        }
    )
)
