# ruff: noqa: F403, F405
from nxd_spec import *

spec = (
    data_product(
        name="market-fraud-density",
        domain="FINANCE/FRAUD-DETECTION",
        description=(
            "Consolidated fraud density metrics by merchant market category. "
            "Provides per-category transaction volume, fraud event count, and fraud rate "
            "percentage. Sourced from the BankSim1 dataset via the Kaggle API in "
            "scheduled daily batches. Compliant with financial auditing standards — no PII."
        ),
        version="1.0.0-dev",
        infra_profile="ecommerce-demo",
    )
    .environment("demo")
    .with_global_trigger(ScheduleTrigger("0 */8 * * *"))
    .transform(
        code(transform)
        .compute("https://app.partner.nextopia.dev/infra-profile/ecommerce-demo#/services/k8s-compute")
        .config(k8s_executor_config)
    )
    .output(
        data_product_output()
        .promise(banksim_transactions_model)
        .promise(fraud_density_model)
        .port(
            "object-storage",
            storage("https://app.partner.nextopia.dev/infra-profile/ecommerce-demo#/services/s3-output")
            .config(s3_config(file_type=SupportedFormat.CSV))
            .promise(
                custom("banksim-transactions-quality")
                .description(
                    "Zero-Null check: category and fraud must have no null values. Amount must be non-negative."
                )
                .model(banksim_transactions_model)
                .verify(code(check_banksim_transactions_quality)),
            )
            .promise(
                custom("fraud-density-quality")
                .description(
                    "Validates uniqueness of market_type, fraud_rate_pct in [0–100], "
                    "transaction_count > 0, and zero-null market_type."
                )
                .model(fraud_density_model)
                .verify(code(check_fraud_density_quality)),
            ),
        )
    )
    .output(
        data_product_rpc_output()
        .function(
            rpc_function(
                code(get_all_fraud_stats),
                FraudDensityAPI.get_all_request_model(),
                FraudDensityAPI.get_all_response_model(),
            ).description(
                "Returns the full ranked list of all merchant market categories with "
                "transaction volume and fraud rate. Enables Power BI slicers and "
                "AI agent comparisons across all markets."
            )
        )
        .function(
            rpc_function(
                code(get_market_fraud_stats),
                FraudDensityAPI.get_stats_request_model(),
                FraudDensityAPI.get_stats_response_model(),
            ).description(
                "Returns fraud density statistics for a single merchant market category. "
                "Supports targeted AI agent queries and Power BI drill-through."
            )
        )
        .port(
            "mcp-api",
            rpc_server("https://app.partner.nextopia.dev/infra-profile/ecommerce-demo#/services/mcp-api-service-k8s")
            .enable_endpoints()
            .mcp_path("/mcp"),
        )
    )
    .control("data-product-access", data_product_access().user("chaithanya.chowdhary@datacolor.ai"))
    .control("steward", data_product_access().user("chaithanya.chowdhary@datacolor.ai"))
    .control("owner", owner().user("chaithanya.chowdhary@datacolor.ai"))
)
