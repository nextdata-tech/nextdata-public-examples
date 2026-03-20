# ruff: noqa: F403, F405
from nxd_models import *

dividends = semantic_model(
    name="dividends",
    description="Dividends paid to shareholders across AU banks",
    attributes=[
        attribute(name="bank", data_type=string()),
        attribute(name="payment_date", data_type=date32()),
        attribute(name="dividend_per_share", data_type=decimal(4, 2)),
    ],
).sampling(method=SamplingMethod.Random)
