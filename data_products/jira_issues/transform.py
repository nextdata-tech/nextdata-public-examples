"""Jira-issues-embeddings transform.

Retrieve all Atlassian Jira issues in project MARS via
``/rest/api/3/search/jql`` (paginated with ``nextPageToken``), concatenate
the free-text fields per issue, chunk them with
``RecursiveCharacterTextSplitter(chunk_size=512)``, embed each chunk with
sentence-transformers ``all-MiniLM-L6-v2`` (384-dim), and write through
``langchain_postgres.PGVectorStore`` into the pgvector instance. Core
fields (id, key, project, status, created, updated) ride along as
metadata.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGEngine, PGVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from nxd.data_product.context import API, PgVector
import psycopg
import requests

_logger = logging.getLogger("transform.jira_embeddings")
_logger.setLevel(logging.INFO)


_PROJECT = "NXD"
# NOTE: the NXD project has been quiet since 2026-04 (active work moved to
# NEX) — a 30-day window matches nothing. 180 days keeps the product
# non-empty; switch _PROJECT to "NEX" to track the active board.
_JQL = f"project = {_PROJECT} AND updated >= -180d"
_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_EMBEDDING_DIMS = 384            # all-MiniLM-L6-v2 output dim
_CHUNK_SIZE = 512
_DEFAULT_TABLE = "jira_issue_embeddings"
_OUTPUT_MODEL_NAME = "jira_issue_embeddings"
_FIELDS = "summary,description,comment,status,project,created,updated"


def _fetch_all_issues(jira: API) -> list[dict[str, Any]]:
    """Page through ``/rest/api/3/search/jql`` collecting every issue.

    The endpoint returns ``nextPageToken`` whenever more results exist;
    we keep posting with that token until the field is absent. ``fields``
    is restricted to the columns we actually need so the response stays
    small."""
    base = str(jira.url).rstrip("/")
    auth = (str(jira.username), str(jira.token))
    issues: list[dict[str, Any]] = []
    next_token: str | None = None
    page = 0
    while True:
        body: dict[str, Any] = {
            "jql": _JQL,
            "fields": _FIELDS.split(","),
            "maxResults": 100,
        }
        if next_token:
            body["nextPageToken"] = next_token
        resp = requests.post(
            f"{base}/rest/api/3/search/jql", json=body, auth=auth, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("issues", [])
        issues.extend(batch)
        page += 1
        _logger.info("Fetched page %d: %d issues (total %d)", page, len(batch), len(issues))
        next_token = data.get("nextPageToken")
        if not next_token:
            break
    return issues


def _adf_to_text(node: Any) -> str:
    """Flatten an Atlassian Document Format (ADF) node tree to plain text.

    Jira Cloud's v3 REST API returns rich-text fields (`description`,
    comment bodies) as ADF dicts, not strings. Collect every `text` leaf,
    joining block-level nodes with newlines.
    """
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(t for t in (_adf_to_text(n) for n in node) if t)
    if isinstance(node, dict):
        if "text" in node and isinstance(node["text"], str):
            return node["text"]
        return _adf_to_text(node.get("content"))
    return str(node)


def _extract_text_blob(issue: dict[str, Any]) -> str:
    """Concatenate summary + description + every comment into one blob."""
    fields = issue.get("fields", {}) or {}
    parts = [
        _adf_to_text(fields.get("summary")),
        _adf_to_text(fields.get("description")),
    ]
    comment_field = fields.get("comment") or {}
    for c in comment_field.get("comments", []) or []:
        body = _adf_to_text(c.get("body"))
        if body:
            parts.append(body)
    return "\n\n".join(p for p in parts if p)


def _metadata(issue: dict[str, Any]) -> dict[str, Any]:
    """Core non-free-text fields kept as vector-store row metadata."""
    fields = issue.get("fields", {}) or {}
    status = (fields.get("status") or {}).get("name")
    project = (fields.get("project") or {}).get("key")
    return {
        "issue_id": issue.get("id"),
        "key": issue.get("key"),
        "project": project,
        "status": status,
        "created": fields.get("created"),
        "updated": fields.get("updated"),
    }


def _chunked_documents(issues: list[dict[str, Any]]) -> tuple[list[Document], list[str]]:
    """Per-issue: chunk the free-text blob and tag each chunk with the
    issue's metadata. Returns a flat list of LangChain Documents plus a
    parallel list of DETERMINISTIC row ids (uuid5 of issue key + chunk
    index) — without stable ids every scheduled run would re-insert the
    same chunks under fresh random UUIDs and the table would fill with
    duplicates; with them the ON CONFLICT upsert refreshes rows in place."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=_CHUNK_SIZE)
    docs: list[Document] = []
    ids: list[str] = []
    for issue in issues:
        blob = _extract_text_blob(issue)
        if not blob.strip():
            continue
        meta = _metadata(issue)
        issue_ref = issue.get("key") or issue.get("id") or "unknown"
        for i, chunk in enumerate(splitter.split_text(blob)):
            docs.append(Document(page_content=chunk, metadata=meta))
            ids.append(str(uuid.uuid5(uuid.NAMESPACE_URL, f"jira:{issue_ref}:{i}")))
    _logger.info("Built %d chunked documents from %d issues", len(docs), len(issues))
    return docs, ids


def _resolve_table(pgvector: PgVector) -> str:
    return (pgvector.model_tables or {}).get(_OUTPUT_MODEL_NAME, _DEFAULT_TABLE)


def _ensure_unique_id_index(pgvector: PgVector, schema: str, table: str) -> None:
    """Create the unique index on ``langchain_id`` if it is missing."""
    with psycopg.connect(
        host=str(pgvector.host),
        port=int(str(pgvector.port)),
        user=str(pgvector.user),
        password=str(pgvector.password),
        dbname=str(pgvector.database),
        autocommit=True,
    ) as conn:
        conn.execute(
            f'CREATE UNIQUE INDEX IF NOT EXISTS "{table}_langchain_id_key" '
            f'ON "{schema}"."{table}" (langchain_id);'
        )


def transform(jira: API, pgvector: PgVector) -> None:
    """Entrypoint bound by spec.py — input port `jira` (API) ->
    output port `pgvector` (PgVector)."""
    issues = _fetch_all_issues(jira)
    docs, doc_ids = _chunked_documents(issues)
    if not docs:
        _logger.info("No documents to embed; nothing to write.")
        return

    table = _resolve_table(pgvector)
    schema = pgvector.schema or "public"
    _logger.info("Target table: %s.%s", schema, table)

    conn_str = (
        f"postgresql+psycopg://{pgvector.user}:{pgvector.password}"
        f"@{pgvector.host}:{pgvector.port}/{pgvector.database}"
    )
    pg_engine = PGEngine.from_connection_string(url=conn_str)

    # `init_vectorstore_table` is a no-op-style DDL on subsequent runs
    # only because the table already exists — the call will *raise* if
    # it does. The NXD pgvector driver provisions the table from the
    # output model before the first run, so this normally raises and is
    # skipped. Wrap so either creation order works.
    try:
        pg_engine.init_vectorstore_table(
            vector_size=_EMBEDDING_DIMS,
            table_name=table,
            schema_name=schema,
        )
        _logger.info("Initialised vectorstore table %s.%s", schema, table)
    except Exception as exc:                                  # noqa: BLE001
        _logger.info("init_vectorstore_table skipped (likely exists): %s", exc)

    # PGVectorStore.add_documents upserts with ON CONFLICT (langchain_id),
    # which requires a unique index. langchain's own DDL creates it as a
    # PRIMARY KEY, but the NXD-provisioned table has no key — ensure it.
    _ensure_unique_id_index(pgvector, schema, table)

    embeddings = HuggingFaceEmbeddings(model_name=_EMBEDDING_MODEL)
    store = PGVectorStore.create_sync(
        engine=pg_engine,
        embedding_service=embeddings,
        table_name=table,
        schema_name=schema,
    )
    # Write in batches: a single add_documents call for the whole corpus
    # holds one giant INSERT transaction open — gentler on the server and,
    # with deterministic ids, an interrupted run resumes idempotently.
    batch = 500
    for start in range(0, len(docs), batch):
        store.add_documents(docs[start : start + batch], ids=doc_ids[start : start + batch])
        _logger.info("Wrote chunks %d-%d of %d", start, min(start + batch, len(docs)), len(docs))
    _logger.info("Wrote %d embedded chunks to %s.%s", len(docs), schema, table)
