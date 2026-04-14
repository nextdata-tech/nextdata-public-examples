# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

This is the `examples_public` git submodule of the `nextdata-examples` monorepo. It contains public-facing NXD data product examples. The parent repo's `CLAUDE.md` covers commands, deployment, and core architecture — read it first.

## Data Products by Pattern

| Pattern | Reference Product | Key Files |
|---|---|---|
| Batch → ADLS (Parquet) | `credit_card_tx` | spec, transform, models, utils, contracts/ |
| External API → ADLS (JSON) | `financial_statements` | spec, transform, utils, \_\_mcp\_\_.py |
| Snowflake → MCP server | `example_mcp` | spec, \_\_mcp\_\_.py |
| Databricks batch (Spark) | `taxi-trip-metrics` | spec, transform |
| Databricks streaming (S3 → Unity Catalog) | `customer_purchases` | spec, transform |
| Snowflake + Databricks + MCP | `loans_products` | spec, transform, models |
| YAML manifest + MCP | `competitor_growth_analysis` | manifest.yaml, \_\_mcp\_\_.py |

## Key Patterns

### nxd_spec.py / nxd_models.py

Every product has these shim files. They exist so `spec.py` can satisfy the single-import rule. They also define shared infra config:

```python
# nxd_spec.py — customized per product
k8s_executor_config = {"memory": "2Gi", "cpu": "500m", ...}
cluster_config = {"spark_version": "...", "node_type_id": "..."}
```

Copy these from a similar product when creating a new one.

### Context Injection in transform.py

Contexts are injected by the platform — never instantiated manually. The function signature for K8s-based products:

```python
def transform(adls: AzureDataLakeStorage, api: API) -> None:
    path = adls.model_paths["my_model"].path
```

For Databricks batch:
```python
@data_product.on_transform()
def transform(db: DatabricksWrite, spark: SparkSession) -> None:
    table = db.full_table_name("my_model")
```

For Databricks streaming:
```python
@data_product.on_transform()
def transform(s3: S3Input, db: DatabricksWrite, spark: SparkSession) -> None:
    # use NxdDatabricksSession.connect() wrapper for per-batch verification
```

### Contracts

Contracts live in `contracts/` and use the `@data_product.on_verify()` decorator:

```python
@data_product.on_verify()
def verify(context: AzureDataLakeStorage, models: dict) -> VerifyResult:
    return VerifyResult(VerifyResultEnum.PASS, {"checked": True})
```

Declared in `spec.py` via `.output(...).promise(contract(...))`.

### MCP Endpoints

`__mcp__.py` exposes RPC functions as AI agent tools:

```python
@function()
@mcp.tool()
def query_data(req: RequestModel, db: Snowflake) -> ResponseModel:
    ...
```

Declared in `spec.py` via `.output(data_product_rpc_output()).function(...).port("mcp-api")`.

### utils.py

ADLS helper functions (read/write parquet, connect to storage) are intentionally duplicated per product — do not refactor into a shared library.

## Feature Matrix

See [`data_products/feature_matrix_table.md`](data_products/feature_matrix_table.md) for a full overview of which infrastructure targets and capabilities each product uses.
