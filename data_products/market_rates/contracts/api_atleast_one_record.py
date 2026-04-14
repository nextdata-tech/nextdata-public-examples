import logging

from nxd.data_product.context import API
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum

_logger = logging.getLogger("contracts.api_atleast_one_record")


def verify(api: API) -> VerifyResult:
    """Verify that the API source endpoint is reachable and returns at least one record."""
    _logger.info("Checking API source availability")
    try:
        response = api.get()
        if response is None:
            return VerifyResult(VerifyResultEnum.FAILED, {"error": "API returned no response"})
        record_count = len(response) if hasattr(response, "__len__") else 1
        if record_count == 0:
            return VerifyResult(VerifyResultEnum.FAILED, {"error": "API returned empty response"})
        return VerifyResult(VerifyResultEnum.PASS, {"record_count": record_count})
    except Exception as e:
        _logger.error(f"API source check failed: {e}")
        return VerifyResult(VerifyResultEnum.FAILED, {"error": str(e)})
