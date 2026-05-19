# ruff: noqa: F403, F405
from nxd_models import *

wttr_model = semantic_model(
    name="wttr",
    description="Current weather observations from the wttr.in public API, normalized to the canonical weather schema.",
).schema(
    {
        "city": (string(), "City name."),
        "timestamp": (
            timestamp(unit=DurationUnit.Milliseconds, timezone="UTC"),
            "Observation time in UTC.",
        ),
        "temperature_c": (float64(), "Air temperature in degrees Celsius."),
        "humidity_pct": (int64(), "Relative humidity percentage (0–100)."),
        "wind_speed_kmh": (float64(), "Wind speed in kilometers per hour."),
    }
)
