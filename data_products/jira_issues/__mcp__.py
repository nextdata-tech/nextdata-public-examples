"""MCP tools for the jira-issues DP — semantic search over the embeddings.

Exposed through the DP's RPC output port (`/rpcs/mcp-api/mcp/`). The search
tool embeds the query with the same model the transform uses
(`all-MiniLM-L6-v2`) and runs a cosine-distance search against the
``jira_issue_embeddings`` pgvector table.

NOTE: the RPC runtime executes the decorated function in its own namespace —
module-level constants/helpers are NOT visible at call time, so the function
body must be fully self-contained.
"""

from __future__ import annotations

from nxd.data_product.context import PgVector
from nxd.drivers.rpc import Request, Response, function, mcp


@function(name="search_jira_issues")
@mcp.tool(
    name="search_jira_issues",
    description=(
        "Semantic search over Jira issues (summaries, descriptions and "
        "comments). Returns the most relevant text chunks with their issue "
        "key, status and similarity score."
    ),
)
def search_jira_issues(request: Request, pgvector: PgVector) -> Response:
    import json

    import psycopg
    # Heavy import kept inside the function: the RPC server boots fast and
    # torch is only loaded on first use. The loaded model is cached on the
    # sentence_transformers module so subsequent calls skip the ~5s load.
    import sentence_transformers

    query = str(request.get("query", "") or "").strip()
    if not query:
        return Response({"results": "[]", "count": 0})
    top_k = min(int(request.get("top_k") or 5), 25)

    model = getattr(sentence_transformers, "_nxd_query_model", None)
    if model is None:
        model = sentence_transformers.SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        sentence_transformers._nxd_query_model = model
    vector = json.dumps(model.encode(query).tolist())

    schema = pgvector.schema or "public"
    with psycopg.connect(
        host=str(pgvector.host),
        port=int(str(pgvector.port)),
        user=str(pgvector.user),
        password=str(pgvector.password),
        dbname=str(pgvector.database),
    ) as conn:
        rows = conn.execute(
            f'SELECT content, langchain_metadata, '
            f"1 - (embedding <=> %s::vector) AS score "
            f'FROM "{schema}"."jira_issue_embeddings" '
            f"ORDER BY embedding <=> %s::vector LIMIT %s",
            (vector, vector, top_k),
        ).fetchall()

    results = []
    for content, metadata, score in rows:
        try:
            meta = json.loads(metadata) if isinstance(metadata, str) else (metadata or {})
        except json.JSONDecodeError:
            meta = {}
        results.append(
            {
                "content": content,
                "issue_key": meta.get("key"),
                "status": meta.get("status"),
                "updated": meta.get("updated"),
                "score": round(float(score), 4),
            }
        )

    return Response({"results": json.dumps(results), "count": len(results)})
