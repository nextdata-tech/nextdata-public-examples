# ruff: noqa: F403, F405
from nxd_models import *

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
    .schema(
        {
            "account_id": (string(), "Unique CRM identifier for the account (e.g. '0013x000001')."),
            "account_type": (string(), "Whether the account is an individual 'Person' or an 'Organization'."),
            "first_name": (string(), "Given name of the person account; blank for organization accounts."),
            "last_name": (string(), "Family name of the person account; blank for organization accounts."),
            "hco_name": (string(), "Healthcare organization name; populated for organization accounts, blank for person accounts."),
            "npi": (int64(), "National Provider Identifier, the unique 10-digit healthcare provider number."),
            "specialty": (string(), "Primary medical specialty of the account (e.g. Cardiology, Oncology, Primary Care)."),
            "city": (string(), "City where the account is located."),
            "state": (string(), "Two-letter US state code where the account is located."),
            "prescribing_decile": (int64(), "Prescribing volume decile from 1 (lowest) to 10 (highest) relative to peers."),
            "segment": (string(), "Strategic value segment of the account (A, B, or C)."),
            "account_value_tier": (string(), "Categorical value tier of the account (High, Medium, or Low)."),
            "potential_value_usd": (int64(), "Estimated total addressable revenue opportunity for the account, in USD."),
            "actual_value_usd": (int64(), "Realized revenue attributed to the account to date, in USD."),
            "preferred_channel": (string(), "Account's preferred engagement channel (e.g. F2F, Remote, Email, Phone, Conference)."),
            "email_opt_in": (boolean(), "Whether the account has consented to receive marketing/email communications."),
            "target_flag": (string(), "Whether the account is on the active call plan / target list ('Y' or 'N')."),
            "territory_id": (string(), "Identifier of the sales territory the account belongs to (e.g. 'T-01')."),
            "primary_rep_id": (string(), "Identifier of the sales representative primarily responsible for the account (e.g. 'R-001')."),
            "status": (string(), "Lifecycle status of the account (e.g. Active, Inactive)."),
        }
    )
)

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
    .schema(
        {
            "activity_id": (string(), "Unique identifier for the engagement activity (e.g. 'a0G000001')."),
            "account_id": (string(), "Identifier of the account the activity was logged against; joins to account.account_id."),
            "rep_id": (string(), "Identifier of the sales representative who performed the activity (e.g. 'R-001')."),
            "territory_id": (string(), "Identifier of the sales territory in which the activity occurred (e.g. 'T-01')."),
            "activity_datetime": (timestamp(unit=DurationUnit.Nanoseconds), "Date and time the activity took place."),
            "activity_month": (string(), "Calendar month of the activity in 'YYYY-MM' format, derived from activity_datetime."),
            "channel": (string(), "Channel through which the activity was conducted (e.g. F2F, Remote, Email, Phone, Virtual Event)."),
            "activity_type": (string(), "Type of engagement (e.g. Detail, Sample Drop, Follow-up, Medical Inquiry)."),
            "product_discussed": (string(), "Product or SKU discussed during the activity (e.g. 'Cardivex 10mg', 'Neurolyn')."),
            "detail_priority": (int64(), "Priority ranking of the product detail during the activity (1 = primary, higher = lower priority)."),
            "duration_min": (int64(), "Duration of the activity in minutes."),
            "engagement_score": (int64(), "Computed engagement quality score for the activity (0-100)."),
            "response": (string(), "Account's response or sentiment to the activity (Positive, Neutral, or Negative)."),
            "on_preferred_channel": (boolean(), "Whether the activity was conducted via the account's preferred channel."),
            "sample_dropped": (boolean(), "Whether product samples were dropped during the activity."),
            "sample_quantity": (int64(), "Quantity of product samples left with the account; 0 when no samples were dropped."),
            "estimated_cost_usd": (int64(), "Estimated cost of conducting the activity, in USD."),
            "next_best_action": (string(), "Recommended follow-up action for the account (e.g. 'Schedule follow-up detail', 'Send approved email')."),
            "follow_up_required": (boolean(), "Whether a follow-up is required as a result of this activity."),
        }
    )
)
