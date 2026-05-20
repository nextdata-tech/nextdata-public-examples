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
            "segment": (string(), "Field-force value segment (A/B/C/D)."),
            "account_value_tier": (string(), "Value tier (High, Medium, or Low)."),
            "email_opt_in": (boolean(), "Whether the account consented to email."),
            "territory_id": (string(), "Sales territory the account belongs to."),
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
        }
    )
)

data_quality_findings = (
    semantic_model(
        name="data_quality_findings",
        description=(
            "Referential-integrity and data-quality findings on the upstream "
            "crm-activity feed: orphan activities, invalid NPIs, inconsistent "
            "casing, missing opt-in, and inactive accounts with activity."
        ),
    )
    .sampling(SamplingMethod.Random)
    .schema(
        {
            "finding_type": (
                string(),
                "Category: orphan_activity, invalid_npi, inconsistent_casing, "
                "missing_email_opt_in, or inactive_account_with_activity.",
            ),
            "entity_type": (string(), "'account' or 'activity'."),
            "entity_id": (string(), "account_id or activity_id the finding relates to."),
            "detail": (string(), "Human-readable description of the issue."),
        }
    )
)
