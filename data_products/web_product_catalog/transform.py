import logging

from ingestion import fetch_catalog
from loader import load_to_snowflake
from nxd.core.context import Snowflake
from nxd.data_product.context import API

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)


def transform(catalog_source: API, snowflake: Snowflake) -> None:
    df = fetch_catalog(catalog_source)
    load_to_snowflake(df, snowflake, table=snowflake.model_tables["catalog_products"])
