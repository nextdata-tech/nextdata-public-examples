def coverage_flag(
    account_value_tier: str,
    potential_value_usd: float,
    actual_value_usd: float,
    touch_count: int,
    pos_count: int,
    neg_no_resp: int,
    f2f_count: int,
) -> str:
    tier = (account_value_tier or "").upper()
    realization = actual_value_usd / potential_value_usd if potential_value_usd > 0 else 0.0

    if tier == "HIGH" and potential_value_usd > 0 and realization < 0.25 and touch_count <= 2:
        return "Under-served high-value"
    if tier == "HIGH" and touch_count >= 3 and pos_count == touch_count:
        return "Well-served high-value"
    if tier == "LOW" and f2f_count >= 1 and neg_no_resp >= 1:
        return "Over-served low-value"
    return "Adequate"
