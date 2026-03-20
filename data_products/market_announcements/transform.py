import logging
from datetime import date

import pyarrow as pa
import pyarrow.compute as pc
from nxd import data_product
from nxd.data_product.context import AzureDataLakeStorage
from utils import bytes_to_adls
from utils import file_exists_adls
from utils import parquet_to_adls

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)


@data_product.on_transform()
def transform(
    adls: AzureDataLakeStorage,
) -> None:
    from api import ASXMarkitDigital
    from models import announcements as announcements_model
    from models import companies as companies_model

    _logger.info("Starting markit-digital-source transformation...")

    asx = ASXMarkitDigital()

    companies = pa.Table.from_pylist([c.model_dump() for c in asx.get_companies_directory_file()])

    announcements = pa.Table.from_pylist(
        # NOTE pagination is not used since you can just increase the items_per_page
        #   there could be an upper limit but the api doesn't imply there is
        [
            c.model_dump()
            for c in asx.get_markets_announcements(
                xids=[
                    "283907",  # WBC
                    # "70547",  # CBA
                    "46090",  # ANZ
                    # "208940",  # NAB
                    "197202",  # MQG
                ],
                date_start=date(2020, 1, 1),  # limit to >2020
                price_sensitive_only=True,
            )
        ]
    )
    # add path column(s)
    announcements = announcements.add_column(
        0,
        "path",
        pc.binary_join_element_wise(  # type: ignore
            "file", announcements["symbol"], announcements["document_key"], "/"
        ),
    )
    announcements = announcements.add_column(
        1,
        "full_path",
        pc.binary_join_element_wise(  # type: ignore
            f"https://{adls.account_name}.dfs.core.windows.net/{adls.container}",
            announcements["path"],
            "/",
        ),
    )

    parquet_to_adls(adls, companies, adls.model_paths[companies_model.name].path)
    parquet_to_adls(adls, announcements, adls.model_paths[announcements_model.name].path)

    # download files to adls
    files = announcements.select(["path", "document_key"]).to_pylist()
    for file in files:
        path, document_key = file.values()

        if path is None or document_key is None:
            _logger.warning(f"document_key or path is missing from: {file}")
            continue

        if file_exists_adls(adls, path):
            _logger.info(f"skipping file: {document_key}, it has already been downloaded to path: {path}")
            continue

        bytes_io = asx.get_file(document_key)
        bytes_to_adls(adls, bytes_io, path)

    _logger.info("Transform completed successfully")


if __name__ == "__main__":
    data_product.main()
