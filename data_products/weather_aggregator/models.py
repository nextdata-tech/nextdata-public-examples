# ruff: noqa: F403, F405
from nxd_models import *

unified_weather_model = (
    semantic_model(
        name="unified_weather",
        description="Unified weather observations aggregated from all provider loaders, "
        "enriched with a provider field indicating the data source.",
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
            "provider": (string(), "Source weather API provider (e.g. open-meteo, wttr.in)."),
            "process_timestamp": (
                timestamp(unit=DurationUnit.Milliseconds, timezone="UTC"),
                "UTC timestamp when the aggregation transform ran.",
            ),
        }
    )
    .sampling(SamplingMethod.Head, 20)
)


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


open_meteo_model = semantic_model(
    name="open_meteo",
    description="Current weather observations from the Open-Meteo public API, "
    "normalized to the canonical weather schema.",
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
