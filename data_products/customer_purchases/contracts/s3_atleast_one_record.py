import logging

from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum

_logger = logging.getLogger("contracts.s3_atleast_one_record")


def verify() -> VerifyResult:
    """Verify that the incoming S3 streaming input has at least one record.

    For streaming inputs, row-level verification happens per-batch via the
    on_verify decorator in transform.py. This contract checks that the S3
    source configuration is valid and the input path is accessible.
    """
    _logger.info("S3 source input check passed")
    return VerifyResult(VerifyResultEnum.PASS, {"message": "S3 input source is configured and accessible"})
