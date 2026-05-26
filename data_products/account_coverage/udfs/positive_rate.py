def positive_rate(pos_count: int, touch_count: int) -> float:
    if touch_count > 0:
        return round(pos_count / touch_count, 4)
    return 0.0
