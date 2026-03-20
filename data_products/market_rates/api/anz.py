import json
import logging
from datetime import datetime
from datetime import timezone

import requests
from azure.storage.filedatalake import DataLakeFileClient

_logger = logging.getLogger("api.anz")
_logger.setLevel(logging.INFO)


def _get_raw_product_data() -> dict:
    current_timestamp = int(datetime.now(timezone.utc).timestamp())
    response = requests.get(
        "https://www.anz.com/productdata/productdata.asp",
        params={
            "output": "json",
            "callback": "callbackFunction",
            "country": "AU",
            "section": "",
            "subsection": "",
            "_": current_timestamp,
        },
    )
    json_body = response.text.removeprefix("callbackFunction(").removesuffix(")")
    return json.loads(json_body)


def _extract_product_data(raw_data: dict) -> list[dict]:
    return raw_data["productdata"][0]["country"][0]["interestrates"][0][
        "section"
    ]  # fmt: off


def sync_product_data(file_client: DataLakeFileClient):
    raw_product_data = _get_raw_product_data()
    product_data = _extract_product_data(raw_product_data)
    serialised_data = json.dumps(product_data)
    file_client.upload_data(serialised_data, overwrite=True)
    _logger.info("Synced ANZ Product Data")
