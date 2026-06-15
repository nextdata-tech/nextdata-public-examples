"""Run the jira-issues-embeddings transform locally against real services.

Loads service credentials from environment variables (or a `.env` file
beside this script — see `.env.example`) and synthesises the runtime
context objects so ``transform()`` is invoked exactly as the platform
would invoke it.
"""

from __future__ import annotations

import logging
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

from nxd.core.context import SecretString
from nxd.data_product.context import API, PgVector

from transform import transform

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(f"Required environment variable '{name}' is not set")
    return value


if __name__ == "__main__":
    jira = API(
        _inner={
            "url": _require("JIRA_URL"),
            "username": _require("JIRA_USERNAME"),
            "token": _require("JIRA_TOKEN"),
        }
    )

    pgvector = PgVector(
        host=_require("PG_HOST"),
        port=int(os.environ.get("PG_PORT", "5432")),
        user=_require("PG_USER"),
        secret_password=SecretString(_require("PG_PASSWORD")),
        database=_require("PG_DATABASE"),
        schema=os.environ.get("PG_SCHEMA", "public"),
        model_tables={"jira_issue_embeddings": os.environ.get(
            "PG_TABLE", "jira_issue_embeddings"
        )},
        models={},
    )

    transform(jira, pgvector)
