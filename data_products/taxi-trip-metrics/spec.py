# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="taxi-trip-metrics",
        description="NYC taxi trip analytics with aggregated metrics by pickup zone, demonstrating Databricks provisioning with custom table creation and data masking",
        domain="ANALYTICS/TRANSPORTATION",
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-examples/data_products/taxi-trip-metrics",
    )
    .environment("demo")
    .provision(
        script("transform/provision.py").compute(
            "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks"
        )
    )
    # Transform with DAB job configuration - execution happens in the pre-deployed bundle job
    .transform(
        script("transform/transform.py")
        .compute(
            "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks"
        )
        .when(any_of(scheduled("*/10 * * * *"), on_started()))
    )
    .output(
        data_product_output()
        .model(pipeline_summary)
        .model(trip_metrics)
        .promise(pipeline_summary)
        .promise(trip_metrics)
        .port(
            "databricks",
            storage(
                "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/nxd-databricks-storage"
            ).config(
                databricks_config().disable_provisioning()  # disable built-in provisioning since we're doing custom provisioning and runs after built-in provisioning. This will change.
            ),
        )
    )
    .control("owner", owner().user("hello@nextdata.com"))
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
)
