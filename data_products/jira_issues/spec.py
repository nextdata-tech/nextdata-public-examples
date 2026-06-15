# ruff: noqa: F403, F405
import types

from nxd_spec import *


def _rpc_with_resources(port_spec, resources):
    """Set pod resources on an RPC output port.

    Workaround: `RpcOutputPortSpec` doesn't expose pod resources yet, but the
    kubernetes/rpc driver reads a flattened `resources` key from the port
    config. The search tool lazy-loads sentence-transformers/torch, which
    OOMs the 512Mi default limit.
    """
    original = port_spec._build_config

    def patched(self, scripts):
        cfg = original(scripts)
        cfg["resources"] = resources
        return cfg

    port_spec._build_config = types.MethodType(patched, port_spec)
    return port_spec


spec = (
    data_product(
        name="jira",
        description="Atlassian Jira issues (project NXD) retrieved via "
        "the REST API, with free-text fields (summary, description, "
        "comments) chunked, embedded with sentence-transformers "
        "`all-MiniLM-L6-v2`, and persisted to pgvector for semantic "
        "search. Other core fields ride along as metadata.",
        domain="engineering",
        # NOTE: kept at the previously published dev version on purpose —
        # dev images overwrite in place WITHOUT the schema-evolution check.
        # A new version number would be validated against the old image's
        # models (which this rework removes/retypes) and 409.
        version="1.0.1-dev",
        infra_profile="ecommerce-demo",
        source_repo_url="https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/jira_issues",
    )
    .environment("demo")
    .input(
        "jira",
        source_aligned_input()
        .source("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/jira-api")
        .model(jira_issue)
        # NOTE: no `.expectation(jira_issue)` — model (schema) expectations
        # are not supported on an `nxd:api` source: the unmanaged API has no
        # stored data or schema to verify against. The custom verifier below
        # is the supported form.
        .expectation(
            custom("Jira API Freshness")
            .verify(code(api_source_freshness.verify))
            .description(
                "Jira API must be reachable and returning recent social signal data within the expected freshness window"
            )
        ),
    )
    .output(
        # NOTE: no output-level `.model(jira_issue)` — the input model is
        # already catalogued via the input spec, and declaring it as an
        # output model would make the pgvector driver provision a spurious
        # `jira_issue` table on the port.
        data_product_output()
        .model(jira_issue_embeddings)
        .port(
            "pgvector",
            storage("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/pgvector")
            .config(
                # Model name == physical table name: the pgvector driver
                # provisions the table from the model (CREATE TABLE IF NOT
                # EXISTS <model-name>), and the transform writes through
                # langchain to the same table. The explicit target_table
                # mapping keeps `model_tables` / `location()` accurate.
                #
                # Schema pinned to "public": the pgvector EXTENSION lives in
                # the `public` schema and the driver sets `search_path` to
                # the configured schema only — provisioning a vector column
                # under any other schema fails with `type "vector" does not
                # exist` (42704).
                pg_vector_config("public").target_table(
                    "jira_issue_embeddings", jira_issue_embeddings
                )
            )
            # Port-level promise: registers the model on the port AND
            # verifies the physical table matches the model schema after
            # each run. Must be on the port (not the output level) so the
            # pgvector driver receives the model for provisioning/verify.
            .promise(jira_issue_embeddings),
        )
    )
    .output(
        data_product_rpc_output()
        .function(
            rpc_function(code(search_jira_issues), search_request, search_response).description(
                "Semantic search over the embedded Jira issues (pgvector cosine similarity)."
            )
        )
        .port(
            "mcp-api",
            _rpc_with_resources(
                rpc_server(
                    "https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/mcp-api-service-k8s"
                )
                .enable_endpoints()
                .mcp_path("/mcp"),
                {
                    "requests": {"cpu": "0.5", "memory": "512Mi"},
                    "limits": {"memory": "3Gi"},
                },
            ),
        )
    )
    .transform(
        code(transform)
        .compute("https://app.demo.trynxd.com/infra-profile/ecommerce-demo#/services/k8s-compute")
        # The venv ships torch + sentence-transformers (multi-GB):
        # - importing torch + loading the MiniLM model blows the 512Mi
        #   default memory limit (the pod OOMs before signalling Started,
        #   which surfaces as a misleading "startup timeout"), and
        # - pod init + first import can exceed the 180s default startup
        #   timeout.
        .config(
            {
                "startup_timeout_secs": 600,
                "resources": {
                    "requests": {"cpu": "1", "memory": "1Gi", "ephemeral-storage": "8Gi"},
                    "limits": {"memory": "4Gi"},
                },
            }
        )
        .when(scheduled("*/10 * * * *"), startup=True)
    )
    # TODO: replace placeholder users with real owner / steward / access.
    .control("owner", owner().user("hello@nextdata.com"))
    .control("steward", data_product_access().user("hello@nextdata.com"))
    .control("data-product-access", data_product_access().user("hello@nextdata.com"))
)
