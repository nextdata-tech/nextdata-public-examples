# Spark Streaming Example with Databricks

A data product that demonstrates continuous data streaming to Unity Catalog Delta tables using Databricks Connect or SDK.

## Modes

### 1. Databricks Connect Mode (Real Streaming)

Uses Databricks Connect for real Spark Structured Streaming:

- **How it works**: Connects to a Databricks cluster via Spark Connect protocol
- **Features**: True streaming with `readStream`/`writeStream`, checkpointing, exactly-once semantics
- **Requirements**:
  - Databricks cluster running DBR 15.x+ (Python 3.11 compatible)
  - `cluster_id` configured in infra profile
  - `databricks-connect>=15.4.0,<16.0.0`

### 2. SDK Mode (Batch Simulation)

Uses Databricks SDK with SQL Statement Execution API:

- **How it works**: Executes SQL INSERT statements via SQL warehouse
- **Features**: Lightweight, works with any SQL warehouse, simulates streaming with batch inserts
- **Requirements**:
  - SQL warehouse available
  - `databricks-sdk>=0.30.0`

The transform automatically selects the mode based on available configuration.

## Dependency Configuration

This example uses the simplified packager model:

1. **All dependencies declared in `requirements.txt`** - both NXD packages and external deps
2. **`use_fast_venv_extraction: true`** - compute pods download the pre-built venv from kernel
3. **No special flags needed** - packager reads everything from requirements.txt

```txt
# NXD packages - explicitly declared
nxd.core
nxd.drivers[rpc]
nxd.data_product[notebook,verify-montecarlo,soda,triggers]

# External packages
databricks-connect>=15.4.0,<16.0.0
databricks-sdk>=0.30.0
pandas>=2.2.0
```

**Note**: Do NOT use `nxd.data_product[gx]` or `nxd.drivers[spark]` extras - they conflict with `databricks-connect` due to pandas version requirements.

## How It Works

1. NXD deploys the data product with kubernetes/compute driver
2. Kernel pod builds venv with all dependencies from requirements.txt
3. Compute pod extracts the pre-built venv (fast, ~2-5 seconds)
4. Transform detects available mode and starts streaming/batch inserts
5. Runs indefinitely until the data product is stopped

## Deployment

### Prerequisites

#### 1. Databricks Workspace Setup

- A Databricks workspace with Unity Catalog enabled
- An infra profile with `nxd:databricks/storage:1.0.0` driver configured

#### 2. For Databricks Connect Mode (Real Streaming)

**Create an All-Purpose Cluster:**

```bash
# List existing clusters
curl -s -X GET "https://<workspace-url>/api/2.0/clusters/list" \
  -H "Authorization: Bearer <token>" | jq '.clusters[] | "\(.cluster_id) - \(.cluster_name) - \(.state)"'

# Or create a new cluster via Databricks UI:
# - Use "Personal Compute" or "All-Purpose" cluster policy
# - Select DBR 15.x+ runtime (required for Databricks Connect)
# - Single node is sufficient for testing
```

**Start the Cluster:**

```bash
# Start a terminated cluster
curl -s -X POST "https://<workspace-url>/api/2.0/clusters/start" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"cluster_id": "<your-cluster-id>"}'

# Check cluster state (must be RUNNING)
curl -s -X GET "https://<workspace-url>/api/2.0/clusters/get?cluster_id=<your-cluster-id>" \
  -H "Authorization: Bearer <token>" | jq '.state'
```

**Create Unity Catalog Volume for Checkpoints:**

```bash
# Create a managed volume for streaming checkpoints
curl -s -X POST "https://<workspace-url>/api/2.1/unity-catalog/volumes" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "catalog_name": "nxd_test",
    "schema_name": "governance_demo",
    "name": "checkpoints",
    "volume_type": "MANAGED",
    "comment": "Checkpoints for streaming data products"
  }'
```

**Update Infra Profile with Cluster ID:**

Update the `governance-infra-profile.yaml` (or your infra profile) with your cluster ID:

```yaml
# In the databricks service section:
- key: cluster_id
  value: "<your-cluster-id>"  # e.g., 0107-121025-fja89pcy
```

Then redeploy the infra profile:

```bash
nxd delete infra-profile governance-infra-profile
nxd create infra-profile --filename path/to/governance-infra-profile.yaml
```

#### 3. For SDK Mode (Batch Simulation)

- A SQL warehouse available (no cluster needed)
- SQL warehouse ID configured in infra profile

### Deploy with NXD

```shell
# Deploy the data product
nxd launch --dir examples/features/drivers/spark-streaming --debug-mode

# View logs
nxd logs streaming-example-dev
```

## Files

| File | Description |
|------|-------------|
| `manifest.yaml` | Data product manifest with kubernetes/compute driver |
| `requirements.txt` | All dependencies (NXD + external) |
| `deployment-spec.yaml` | Maps to infra profile services |
| `transform/stream.py` | Streaming transform with both modes |

## Configuration

The data product reads configuration from the NXD Databricks context:

| Field | Description |
|-------|-------------|
| `host` | Databricks workspace URL |
| `token` | OAuth access token (auto-refreshed by NXD) |
| `catalog` | Unity Catalog catalog name |
| `schema` | Unity Catalog schema name |
| `cluster_id` | Cluster ID for Databricks Connect mode (optional) |

## Sample Output

### Databricks Connect Mode
```
[Streaming] Using Databricks Connect mode (real Spark streaming)
[Streaming] Connecting to cluster: 0810-212729-ltku0bm6
[Streaming] Successfully connected to Databricks cluster
[Streaming] Starting rate stream to table: nxd_test.streaming_demo.STREAMING_OUTPUT
```

### SDK Mode
```
[Streaming] Using Databricks SDK mode (batch SQL simulation)
[Streaming] Using SQL warehouse: Starter Warehouse (abc123)
[Streaming] Target table: nxd_test.streaming_demo.STREAMING_OUTPUT
[Streaming] Batch 1: Inserting 10 rows...
```

## Troubleshooting

### Error: `RESOURCE_DOES_NOT_EXIST: No cluster found matching: <cluster-id>`

**Cause**: The cluster ID in the infra profile doesn't exist or has been deleted.

**Fix**:
1. List available clusters and find a valid one
2. Update the infra profile with the correct `cluster_id`
3. Redeploy the infra profile

### Error: `NoSuchVolumeException`

**Cause**: The Unity Catalog volume for checkpoints doesn't exist.

**Fix**: Create the volume using the Unity Catalog API (see Prerequisites section).

### Error: Cluster is `TERMINATED`

**Cause**: The Databricks cluster is not running.

**Fix**: Start the cluster before launching the data product:
```bash
curl -s -X POST "https://<workspace-url>/api/2.0/clusters/start" \
  -H "Authorization: Bearer <token>" \
  -d '{"cluster_id": "<your-cluster-id>"}'
```

### Error: `Data Product failed to start`

**Cause**: Various - check the logs for specific error.

**Debug**:
```bash
nxd logs streaming-example-dev | grep -i "error\|fail\|exception"
```

Common causes:
- Cluster not running
- Missing checkpoint volume
- Invalid credentials
- Network connectivity issues
