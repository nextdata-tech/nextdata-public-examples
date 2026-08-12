import json
import logging

import requests
from azure.storage.filedatalake import DataLakeFileClient

_logger = logging.getLogger("transform.macquarie")

# macquarie.com.au's edge WAF blocks requests that don't look like a real
# browser tab (returns a 403 "Access Denied" HTML page). A bare User-Agent
# wasn't enough; matching a fuller browser header set (Referer, sec-fetch-*,
# Accept-Language) is closer, but the site has also been observed 403-ing
# by source IP regardless of headers — see the None-on-failure handling
# below.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,*/*",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://www.macquarie.com.au/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}


def _fetch_validated_json(url: str) -> str | None:
    """Fetch `url` and return its body if it's valid JSON, else None.

    macquarie.com.au intermittently blocks this scraper (WAF/bot detection,
    observed as a 403 regardless of headers). Rather than fail the whole
    transform run — which would also stop the other 4 models in this DP
    from updating, and cascades to a JSONDecodeError several hops into any
    downstream consumer's contract check — a failure here is logged and the
    caller skips the write, leaving the last-known-good ADLS content in
    place.
    """
    try:
        response = requests.get(url, headers=_BROWSER_HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        _logger.warning("macquarie fetch failed for %s: %s — keeping last-known-good data", url, e)
        return None
    try:
        json.loads(response.text)
    except json.JSONDecodeError:
        _logger.warning(
            "macquarie returned non-JSON for %s (status %s): %r — keeping last-known-good data",
            url,
            response.status_code,
            response.text[:200],
        )
        return None
    return response.text


def sync_term_deposit_data(file_client: DataLakeFileClient):
    content = _fetch_validated_json("https://www.macquarie.com.au/everyday-banking/term-deposits.csvUpload.html")
    if content is not None:
        file_client.upload_data(content, overwrite=True)


def sync_home_loan_data(file_client: DataLakeFileClient):
    content = _fetch_validated_json("https://www.macquarie.com.au/home-loans/home-loan-rates.csvUpload.html")
    if content is not None:
        file_client.upload_data(content, overwrite=True)
