# account-coverage: Developer Reference

## What this document covers

How the three MCP tools work, with emphasis on get_schema's dynamic
schema approach and what to do when things need updating.

---

## Architecture

```
account-coverage DP package
  spec.py / nxd_spec.py          -- DP declaration and tool wiring
  nxd_models.py                  -- nxd DSL imports
  models.py                      -- semantic model definitions (single source of truth)
  __mcp__.py                     -- MCP tool implementations
  transform.sql                  -- Snowpark stored procedure (data pipeline)
  requirements.txt               -- pip dependencies
  udfs/                          -- Snowflake Python UDFs
```

---

## The three tools

### get_schema

Returns the complete ACCOUNT_COVERAGE table schema. Call this before
execute_query to learn exact column names, types, and business definitions.

No Snowflake connection. No extra files. Zero hardcoded descriptions.

### execute_query

Proxies a SQL SELECT through the Snowflake MCP Server (SQL_EXEC_MCP_SRVR
in the ACCOUNT_COVERAGE schema). Claude writes the SQL; Snowflake executes it.
Use for precise structured queries where you know the column names.

### search_accounts

Semantic search over account profiles using Snowflake Cortex Search
(ACCOUNT_COVERAGE_SEARCH service). Use this as the default for any
plain-English question about accounts -- no SQL needed.

---

## How get_schema reads from models.py

This is the key design decision and the reason models.py is the single
source of truth for column descriptions.

```python
# Inside the get_schema function body (nxd restricted scope)
import models

raw_schema = models.account_coverage._schema
# raw_schema is the dict passed to .schema() in models.py:
# {
#   "account_id":        ("string",                              "Unique CRM account identifier..."),
#   "realization_ratio": ({"decimal128": {"precision":6,"scale":4}}, "actual / potential..."),
#   ...
# }

for col_name, (type_val, description) in raw_schema.items():
    # format and emit each column
```

The `_schema` attribute is set by the `semantic_model(...).schema({...})` call
in models.py. The nxd.spec.data_types functions (string(), int64(), decimal())
return plain Python values: a string for simple types, a dict for decimal.

Column order in the output matches the order in models.py (Python 3.7+
dicts preserve insertion order).

### Why this is single source of truth

```
Developer edits models.py
        |
        v
nxd launch
        |
        +-- registers semantic model in platform catalog
        |
        +-- propagates column descriptions as Snowflake column COMMENTs
        |
        v  (at the next get_schema call)
get_schema imports models, reads _schema, returns updated descriptions
```

No separate data file to maintain. No Snowflake connection for get_schema.
Change models.py once, redeploy, and the platform registration, Snowflake
COMMENTs, and get_schema output all reflect the change.

---

## Updating a column description

**Step 1: edit models.py**

```python
"territory_id": (
    string(),
    "Sales territory. Exclude T-MKT (marketing). "
    "Field rep territories: T-01, T-02, T-03, T-04.",
),
```

**Step 2: nxd launch**

```
nxd launch
```

The next get_schema call returns the new description. No changes to
__mcp__.py needed.

---

## Adding a new column

When transform.sql adds a column to the Snowpark result.select():

1. Add it to the Snowpark result.select() in transform.sql.
2. Add a new entry to the account_coverage .schema() dict in models.py
   (in the same position as in the SELECT -- order matters for output).
3. nxd launch.

get_schema will include the new column automatically on the next call.

---

## The _schema attribute and SDK stability

`_schema` is an internal attribute of the nxd.spec.semantic_model class,
not part of the public API. It is the dict passed to .schema() and has been
stable across nxd SDK versions used in this environment.

get_schema defends against a potential SDK change:

```python
raw_schema = getattr(models.account_coverage, "_schema", None)
if raw_schema is None:
    return Response({"schema":
        "ERROR: models.account_coverage._schema not found. "
        "Run vars(models.account_coverage) to find the correct attribute name..."
    })
```

If nxd renames this attribute in a future SDK update, get_schema returns a
clear error message with a specific fix instruction rather than crashing
silently or returning stale data.

To diagnose: deploy a one-line debug function that returns
str(vars(models.account_coverage)) -- this shows all current attribute names.

---

## Error states

| Condition | Response |
|---|---|
| `_schema` attribute not found | `ERROR: models.account_coverage._schema not found. Run: vars(...)` |
| `_schema` is empty | `ERROR: models.account_coverage._schema is empty.` |
| SQL not SELECT/WITH | `Only SELECT or WITH queries are allowed.` |
| SQL is empty string | `No SQL provided.` |
| Empty search query | `No search query provided.` |

No raw Python tracebacks are surfaced to the caller in any case.

---

## What to do when the image build fails (500 error)

The build server validates YAML files it finds in the DP root. Do NOT
add arbitrary .yaml files to the package root -- they will be parsed
as nxd manifests and a 500 will follow if the schema does not match.

Python modules (.py files) in the root are always safe.

---

## Glossary integration (future)

To link columns to a central commercial-analytics glossary DP:

1. Create a commercial-analytics-glossary DP with a glossary.yaml.
2. Add .link() entries in models.py:
   "coverage_flag": (string(), "...", {"relates_to": [{"relationship_type":
     "GlossaryTerm", "name": "commercial-analytics-glossary", "term_id": "coverage_flag"}]})
3. The agent layer (Claude Desktop, nxd proxy) can call
   glossary__get_glossary("commercial-analytics-glossary") to fetch canonical
   term definitions and merge them with get_schema output.
4. No changes to __mcp__.py needed for the glossary link to work at the agent layer.
