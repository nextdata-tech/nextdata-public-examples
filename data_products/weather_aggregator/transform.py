import logging

from models import open_meteo_model
from models import unified_weather_model
from models import wttr_model
from nxd.core.context import Snowflake
from snowflake.snowpark import Session
from snowflake.snowpark.functions import current_timestamp
from snowflake.snowpark.functions import lit

_logger = logging.getLogger("weather_aggregator.transform")


def _session(snowflake: Snowflake) -> Session:
    return Session.builder.configs(
        {
            "account": snowflake.account,
            "user": snowflake.user,
            "password": snowflake.password,
            "warehouse": snowflake.warehouse,
            "database": snowflake.database,
            "schema": snowflake.schema,
        }
    ).create()


def transform(open_meteo_data: Snowflake, wttr_data: Snowflake, snowflake: Snowflake) -> None:
    session = _session(snowflake)

    om_table = open_meteo_data.full_table_name(open_meteo_model.name)
    wttr_table = wttr_data.full_table_name(wttr_model.name)

    om_df = session.table(om_table).with_column("provider", lit("open-meteo"))
    wttr_df = session.table(wttr_table).with_column("provider", lit("wttr.in"))

    unified = om_df.union_all(wttr_df).with_column("process_timestamp", current_timestamp())
    row_count = unified.count()
    target_table = snowflake.model_tables[unified_weather_model.name]
    fq_target_table = snowflake.full_table_name(unified_weather_model.name)
    _logger.info(f"Writing {row_count} unified records to {fq_target_table}")

    unified.write.mode("overwrite").save_as_table(target_table)
    session.close()
    _logger.info(f"Aggregation complete: {row_count} records written")
