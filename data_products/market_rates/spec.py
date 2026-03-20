# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="market-rates",
        domain="FINANCE/COMPETITORS/MARKET-INTELLIGENCE",
        description="Data collected as part of competitor analysis from publicly available websites",
        version="0.0.1-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-examples",
    )
    .input(
        "comp_public",
        source_aligned_input().source(
            "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/yahoo-finance"
        ),
    )
    .input(
        "nextopia_public",
        source_aligned_input().source(
            "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/yahoo-finance"
        ),
    )
    .input(
        "comp2_public",
        source_aligned_input().source(
            "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/yahoo-finance"
        ),
    )
    .environment("demo")
    .transform(
        code(transform)
        .compute(
            "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute"
        )
        .config(k8s_executor_config)
    )
    .with_global_trigger(ScheduleTrigger("0 */8 * * *"))
    .output(
        data_product_output()
        .promise(anz_products)
        .promise(westpac_term_deposits)
        .promise(macquarie_term_deposits)
        .promise(westpac_home_loans)
        .promise(macquarie_home_loans)
        .port(
            "adls",
            storage(
                "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/adls"
            )
            .config(adls_config(file_type=SupportedFormat.JSON))
            .managed_access(),
        )
    )
    .control("owner", owner().user("hello@nextdata.com"))
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
)
