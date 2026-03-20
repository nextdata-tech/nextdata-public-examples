# ruff: noqa: F403, F405
from nxd_models import *

banks = semantic_model(
    name="banks",
    description="A list of banks availble in this data product",
    attributes=[attribute(name="name", data_type=string(), description="Bank name")],
)
