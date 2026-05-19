# ruff: noqa: F403, F405
from nxd_models import *

open_meteo_model = (
    semantic_model(
        name="open_meteo",
        description="Current weather observations from the Open-Meteo public API, "
        "normalized to the canonical weather schema.",
    )
    .schema(
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
    .sampling(SamplingMethod.Head, 20)
)
