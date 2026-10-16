import requests
from nxd.data_product.context import API
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum

# Keep in step with `_JQL` in transform.py: this checks the same window the
# transform reads, so an empty window fails here instead of producing an
# empty table.
_FRESHNESS_JQL = "project = NXD AND updated >= -180d"


def verify(jira: API) -> VerifyResult:
    """Verifies that the Jira API accepts the `jira-api` credentials and has
    issues updated within the transform's freshness window.

    Both checks call Jira directly. A search alone cannot tell the two
    failures apart: Jira Cloud serves a bad token as an anonymous caller,
    returning HTTP 200 with zero issues."""
    base = str(jira.url).rstrip("/")
    auth = (str(jira.username), str(jira.token))
    try:
        me = requests.get(f"{base}/rest/api/3/myself", auth=auth, timeout=30)
        if me.status_code != 200:
            return VerifyResult(
                VerifyResultEnum.FAILED,
                {
                    "result": "Jira rejected the `jira-api` credentials.",
                    "http_status": me.status_code,
                    "remedy": "Rotate the Jira API token and re-apply the infra profile.",
                },
            )

        count = requests.post(
            f"{base}/rest/api/3/search/approximate-count",
            json={"jql": _FRESHNESS_JQL},
            auth=auth,
            timeout=30,
        )
        count.raise_for_status()
        issues = int(count.json().get("count", 0))
    except requests.RequestException as exc:
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {"result": f"Jira API unreachable: {type(exc).__name__}"},
        )

    if issues == 0:
        return VerifyResult(
            VerifyResultEnum.FAILED,
            {
                "result": "No Jira issues updated within the freshness window.",
                "jql": _FRESHNESS_JQL,
            },
        )
    return VerifyResult(
        VerifyResultEnum.PASS,
        {"result": "Jira API reachable with recent issues.", "issues_in_window": issues},
    )
