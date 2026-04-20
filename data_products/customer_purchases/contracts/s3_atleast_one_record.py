import logging
from urllib.parse import urlparse

import boto3
from botocore.exceptions import BotoCoreError
from botocore.exceptions import ClientError
from nxd.data_product.context import S3Input
from nxd.data_product.context import VerifyResult
from nxd.data_product.context import VerifyResultEnum

_logger = logging.getLogger("contracts.s3_atleast_one_record")


def verify(s3_input: S3Input) -> VerifyResult:
    """Verify that the incoming S3 streaming input source is accessible and non-empty."""
    uri = s3_input.model_output_paths[""]
    for attr in ("uri", "url", "path"):
        val = getattr(s3_input, attr, None)
        if isinstance(val, str) and val.strip():
            uri = val.strip()
            break

    if not uri:
        bucket = getattr(s3_input, "bucket", None)
        key = getattr(s3_input, "key", None) or getattr(s3_input, "prefix", None)
        if bucket:
            uri = f"s3://{bucket}/{key.lstrip('/') if key else ''}"

    if not uri:
        msg = "S3 input source is not configured with a usable URI/path"
        _logger.error(msg)
        return VerifyResult(VerifyResultEnum.FAILED, {"message": msg})

    try:
        parsed = urlparse(uri)
        bucket = parsed.netloc
        prefix = parsed.path.lstrip("/")
        s3 = boto3.client("s3")
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        if not response.get("Contents"):
            msg = f"S3 input source is accessible but empty: {uri}"
            _logger.error(msg)
            return VerifyResult(VerifyResultEnum.FAILED, {"message": msg})
    except (ValueError, BotoCoreError, ClientError) as exc:
        msg = f"Unable to access S3 input source '{uri}': {exc}"
        _logger.exception(msg)
        return VerifyResult(VerifyResultEnum.FAILED, {"message": msg})

    _logger.info("S3 source input check passed for %s", uri)
    return VerifyResult(VerifyResultEnum.PASS, {"message": f"S3 input source is accessible and non-empty: {uri}"})
