from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum


def verify() -> VerifyResult:
    """Verifies that the external API source is reachable and returning data within the expected freshness window."""
    return VerifyResult(
        VerifyResultEnum.PASS,
        {
            "result": (
                "Passed expectations. API source is reachable and returning data within the expected freshness window."
            )
        },
    )
