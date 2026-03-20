# ruff: noqa: F403, F405
from nxd_models import *

pipeline_summary = (
    semantic_model(
        name="pipeline_summary",
        description="Summary statistics from data pipeline execution analysis",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "pipeline": (string(), "Pipeline identifier"),
            "status": (string(), "Execution status (success/failed)"),
            "rows_processed": (int32(), "Number of rows processed by the pipeline"),
        }
    )
)

trip_metrics = (
    semantic_model(
        name="trip_metrics",
        description="Aggregated NYC taxi trip metrics by pickup zone",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "pickup_zip": (string(), "Pickup zip code"),
            "trip_count": (int32(), "Total number of trips from this zone"),
            "avg_fare": (float64(), "Average fare amount for trips from this zone"),
        }
    )
)
