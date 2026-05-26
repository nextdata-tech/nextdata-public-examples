def realization_ratio(actual_value_usd: float, potential_value_usd: float) -> float:
    if potential_value_usd > 0:
        return round(actual_value_usd / potential_value_usd, 4)
    return 0.0
