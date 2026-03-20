from nxd.data_product.context import Snowflake
from nxd.drivers.rpc import Request
from nxd.drivers.rpc import Response
from nxd.drivers.rpc import function
from nxd.drivers.rpc import mcp
from snowflake.connector import connect


def configure_logger():
    import logging

    logger = logging.getLogger(__name__)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)
    return logger


logger = configure_logger()


@function(name="get_bank_symbols")
@mcp.tool(
    name="get_bank_symbols",
    description="Retrieve available bank symbols for growth analysis",
)
def get_bank_symbols(
    snowflake: Snowflake,
    request: Request,
) -> Response:
    logger.info(f"Received request: {request}")
    logger.info(f"Using Snowflake context: {snowflake}")
    year = request.get("year", None)

    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()

    query = f"SELECT DISTINCT SYMBOL, DATE FROM {snowflake.model_tables['growth']}"
    if year is not None:
        query += f" WHERE DATE BETWEEN '{year}-01-01' AND '{year}-12-31'"
    cursor.execute(query)

    columns = [col[0].lower() for col in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return Response({"banks": results})


@function(name="get_growth")
@mcp.tool(
    name="get_growth",
    description="Retrieve financial growth and shareholder returns for a given bank for given symbols. Check available symbols with get_bank_symbols tool",
)
def get_growth(
    snowflake: Snowflake,
    request: Request,
) -> Response:
    logger.info(f"Received request: {request}")
    logger.info(f"Using Snowflake context: {snowflake}")
    symbol = request.get("symbol", None)
    if symbol is None:
        return Response({"growth": []})

    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()

    query = f"SELECT SYMBOL, DATE, CLOSE, ANNUAL_RETURN, NET_INCOME, TOTAL_REVENUE, REVENUE_GROWTH, NET_INCOME_GROWTH FROM {snowflake.model_tables['growth']} WHERE SYMBOL ILIKE '%{symbol}%' ORDER BY DATE DESC LIMIT 1000"
    cursor.execute(query)

    columns = [col[0].lower() for col in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    # results = [
    #     # JPM (JPMorgan Chase) 2020-2025
    #     {
    #         "symbol": "JPM",
    #         "date": "2020-12-31",
    #         "close": 127.07,
    #         "annual_return": 0.08,
    #         "net_income": 29131000000,
    #         "total_revenue": 119543000000,
    #         "revenue_growth": 0.03,
    #         "net_income_growth": -0.18,
    #     },
    #     {
    #         "symbol": "JPM",
    #         "date": "2021-12-31",
    #         "close": 158.35,
    #         "annual_return": 0.25,
    #         "net_income": 48334000000,
    #         "total_revenue": 125340000000,
    #         "revenue_growth": 0.05,
    #         "net_income_growth": 0.66,
    #     },
    #     {
    #         "symbol": "JPM",
    #         "date": "2022-12-31",
    #         "close": 134.19,
    #         "annual_return": -0.15,
    #         "net_income": 37676000000,
    #         "total_revenue": 128698000000,
    #         "revenue_growth": 0.03,
    #         "net_income_growth": -0.22,
    #     },
    #     {
    #         "symbol": "JPM",
    #         "date": "2023-12-31",
    #         "close": 170.12,
    #         "annual_return": 0.27,
    #         "net_income": 49552000000,
    #         "total_revenue": 158105000000,
    #         "revenue_growth": 0.23,
    #         "net_income_growth": 0.32,
    #     },
    #     {
    #         "symbol": "JPM",
    #         "date": "2024-12-31",
    #         "close": 234.58,
    #         "annual_return": 0.38,
    #         "net_income": 58100000000,
    #         "total_revenue": 172450000000,
    #         "revenue_growth": 0.09,
    #         "net_income_growth": 0.17,
    #     },
    #     {
    #         "symbol": "JPM",
    #         "date": "2025-12-31",
    #         "close": 251.30,
    #         "annual_return": 0.07,
    #         "net_income": 61200000000,
    #         "total_revenue": 181200000000,
    #         "revenue_growth": 0.05,
    #         "net_income_growth": 0.05,
    #     },
    #     # BAC (Bank of America) 2020-2025
    #     {
    #         "symbol": "BAC",
    #         "date": "2020-12-31",
    #         "close": 30.31,
    #         "annual_return": 0.10,
    #         "net_income": 17894000000,
    #         "total_revenue": 85528000000,
    #         "revenue_growth": -0.07,
    #         "net_income_growth": -0.35,
    #     },
    #     {
    #         "symbol": "BAC",
    #         "date": "2021-12-31",
    #         "close": 44.66,
    #         "annual_return": 0.47,
    #         "net_income": 31978000000,
    #         "total_revenue": 89113000000,
    #         "revenue_growth": 0.04,
    #         "net_income_growth": 0.79,
    #     },
    #     {
    #         "symbol": "BAC",
    #         "date": "2022-12-31",
    #         "close": 33.13,
    #         "annual_return": -0.26,
    #         "net_income": 27528000000,
    #         "total_revenue": 94947000000,
    #         "revenue_growth": 0.07,
    #         "net_income_growth": -0.14,
    #     },
    #     {
    #         "symbol": "BAC",
    #         "date": "2023-12-31",
    #         "close": 34.42,
    #         "annual_return": 0.04,
    #         "net_income": 26513000000,
    #         "total_revenue": 99090000000,
    #         "revenue_growth": 0.04,
    #         "net_income_growth": -0.04,
    #     },
    #     {
    #         "symbol": "BAC",
    #         "date": "2024-12-31",
    #         "close": 45.89,
    #         "annual_return": 0.33,
    #         "net_income": 28450000000,
    #         "total_revenue": 103200000000,
    #         "revenue_growth": 0.04,
    #         "net_income_growth": 0.07,
    #     },
    #     {
    #         "symbol": "BAC",
    #         "date": "2025-12-31",
    #         "close": 48.75,
    #         "annual_return": 0.06,
    #         "net_income": 29800000000,
    #         "total_revenue": 107500000000,
    #         "revenue_growth": 0.04,
    #         "net_income_growth": 0.05,
    #     },
    #     # JBH (J.B. Hunt Transport Services) 2020-2025
    #     {
    #         "symbol": "JBH",
    #         "date": "2020-12-31",
    #         "close": 135.28,
    #         "annual_return": 0.15,
    #         "net_income": 545000000,
    #         "total_revenue": 9168000000,
    #         "revenue_growth": -0.02,
    #         "net_income_growth": -0.12,
    #     },
    #     {
    #         "symbol": "JBH",
    #         "date": "2021-12-31",
    #         "close": 203.89,
    #         "annual_return": 0.51,
    #         "net_income": 801000000,
    #         "total_revenue": 11993000000,
    #         "revenue_growth": 0.31,
    #         "net_income_growth": 0.47,
    #     },
    #     {
    #         "symbol": "JBH",
    #         "date": "2022-12-31",
    #         "close": 178.45,
    #         "annual_return": -0.12,
    #         "net_income": 954000000,
    #         "total_revenue": 13894000000,
    #         "revenue_growth": 0.16,
    #         "net_income_growth": 0.19,
    #     },
    #     {
    #         "symbol": "JBH",
    #         "date": "2023-12-31",
    #         "close": 174.22,
    #         "annual_return": -0.02,
    #         "net_income": 820000000,
    #         "total_revenue": 12942000000,
    #         "revenue_growth": -0.07,
    #         "net_income_growth": -0.14,
    #     },
    #     {
    #         "symbol": "JBH",
    #         "date": "2024-12-31",
    #         "close": 165.80,
    #         "annual_return": -0.05,
    #         "net_income": 775000000,
    #         "total_revenue": 12450000000,
    #         "revenue_growth": -0.04,
    #         "net_income_growth": -0.05,
    #     },
    #     {
    #         "symbol": "JBH",
    #         "date": "2025-12-31",
    #         "close": 182.95,
    #         "annual_return": 0.10,
    #         "net_income": 850000000,
    #         "total_revenue": 13100000000,
    #         "revenue_growth": 0.05,
    #         "net_income_growth": 0.10,
    #     },
    # ]

    # if symbol:
    #     results = [record for record in results if symbol.lower() in record["symbol"].lower()]

    return Response({"growth": results})


@function(name="get_dividend_sustainability")
@mcp.tool(
    name="get_dividend_sustainability",
    description="Retrieve Year-over-year dividend sustainability analysis banks: Bank of America, Citigroup, Westpac",
)
def get_dividend_sustainability(
    snowflake: Snowflake,
    request: Request,
) -> Response:
    logger.info(f"Received request: {request}")
    logger.info(f"Using Snowflake context: {snowflake}")
    bank = request.get("bank", None)
    if bank is None:
        return Response({"bank": []})

    conn = connect(
        user=snowflake.user,
        password=snowflake.password,
        account=snowflake.account,
        warehouse=snowflake.warehouse,
        database=snowflake.database,
        schema=snowflake.schema,
    )
    cursor = conn.cursor()

    query = f"SELECT BANK, YEAR, DIVIDEND_PER_SHARE, OPERATING_CASH_FLOW_THOUSANDS, DIVIDEND_YIELD_TREND, OCF_TREND, DIVIDEND_GROWTH_VS_OCF_GROWTH, SUSTAINABILITY_FLAG FROM {snowflake.model_tables['dividend_sustainability']} WHERE BANK ILIKE '%{bank}%' ORDER BY YEAR DESC LIMIT 1000"
    cursor.execute(query)

    columns = [col[0].lower() for col in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # results = [
    #     # Westpac 2020-2024
    #     {
    #         "bank": "Westpac",
    #         "year": 2020,
    #         "dividend_per_share": 0.62,
    #         "operating_cash_flow_thousands": 18234000000,
    #         "dividend_yield_trend": -0.5161290323,
    #         "ocf_trend": -0.0234567890,
    #         "dividend_growth_vs_ocf_growth": -0.4926722433,
    #         "sustainability_flag": "CONSERVATIVE GROWTH",
    #     },
    #     {
    #         "bank": "Westpac",
    #         "year": 2021,
    #         "dividend_per_share": 1.25,
    #         "operating_cash_flow_thousands": 50387000000,
    #         "dividend_yield_trend": 1.0161290323,
    #         "ocf_trend": 1.7635789123,
    #         "dividend_growth_vs_ocf_growth": -0.74744988,
    #         "sustainability_flag": "CONSERVATIVE GROWTH",
    #     },
    #     {
    #         "bank": "Westpac",
    #         "year": 2022,
    #         "dividend_per_share": 1.34,
    #         "operating_cash_flow_thousands": 16954000000,
    #         "dividend_yield_trend": 0.072,
    #         "ocf_trend": -0.6636778417,
    #         "dividend_growth_vs_ocf_growth": 0.7356778417,
    #         "sustainability_flag": "GROWING FASTER THAN OCF",
    #     },
    #     {
    #         "bank": "Westpac",
    #         "year": 2023,
    #         "dividend_per_share": 1.54,
    #         "operating_cash_flow_thousands": -10796000000,
    #         "dividend_yield_trend": 0.1492537313,
    #         "ocf_trend": -1.63678188,
    #         "dividend_growth_vs_ocf_growth": 1.786035612,
    #         "sustainability_flag": "GROWING FASTER THAN OCF",
    #     },
    #     {
    #         "bank": "Westpac",
    #         "year": 2024,
    #         "dividend_per_share": 1.81,
    #         "operating_cash_flow_thousands": -19767000000,
    #         "dividend_yield_trend": 0.1753246753,
    #         "ocf_trend": 0.8309559096,
    #         "dividend_growth_vs_ocf_growth": -0.6556312343,
    #         "sustainability_flag": "CONSERVATIVE GROWTH",
    #     },
    #     # Bank of America 2020-2024
    #     {
    #         "bank": "Bank of America",
    #         "year": 2020,
    #         "dividend_per_share": 0.72,
    #         "operating_cash_flow_thousands": 45230000000,
    #         "dividend_yield_trend": 0.0,
    #         "ocf_trend": -0.1234567890,
    #         "dividend_growth_vs_ocf_growth": 0.1234567890,
    #         "sustainability_flag": "GROWING FASTER THAN OCF",
    #     },
    #     {
    #         "bank": "Bank of America",
    #         "year": 2021,
    #         "dividend_per_share": 0.84,
    #         "operating_cash_flow_thousands": 52870000000,
    #         "dividend_yield_trend": 0.1666666667,
    #         "ocf_trend": 0.1688945678,
    #         "dividend_growth_vs_ocf_growth": -0.0022279011,
    #         "sustainability_flag": "CONSERVATIVE GROWTH",
    #     },
    #     {
    #         "bank": "Bank of America",
    #         "year": 2022,
    #         "dividend_per_share": 0.92,
    #         "operating_cash_flow_thousands": 58340000000,
    #         "dividend_yield_trend": 0.0952380952,
    #         "ocf_trend": 0.1034567890,
    #         "dividend_growth_vs_ocf_growth": -0.0082186938,
    #         "sustainability_flag": "CONSERVATIVE GROWTH",
    #     },
    #     {
    #         "bank": "Bank of America",
    #         "year": 2023,
    #         "dividend_per_share": 0.96,
    #         "operating_cash_flow_thousands": 61250000000,
    #         "dividend_yield_trend": 0.0434782609,
    #         "ocf_trend": 0.0498712345,
    #         "dividend_growth_vs_ocf_growth": -0.0063929736,
    #         "sustainability_flag": "CONSERVATIVE GROWTH",
    #     },
    #     {
    #         "bank": "Bank of America",
    #         "year": 2024,
    #         "dividend_per_share": 1.04,
    #         "operating_cash_flow_thousands": 64780000000,
    #         "dividend_yield_trend": 0.0833333333,
    #         "ocf_trend": 0.0576234567,
    #         "dividend_growth_vs_ocf_growth": 0.0257098766,
    #         "sustainability_flag": "MODERATE GROWTH",
    #     },
    #     # Citigroup 2020-2024
    #     {
    #         "bank": "Citigroup",
    #         "year": 2020,
    #         "dividend_per_share": 2.04,
    #         "operating_cash_flow_thousands": 38450000000,
    #         "dividend_yield_trend": -0.0476190476,
    #         "ocf_trend": -0.2345678901,
    #         "dividend_growth_vs_ocf_growth": 0.1869488425,
    #         "sustainability_flag": "GROWING FASTER THAN OCF",
    #     },
    #     {
    #         "bank": "Citigroup",
    #         "year": 2021,
    #         "dividend_per_share": 2.04,
    #         "operating_cash_flow_thousands": 45230000000,
    #         "dividend_yield_trend": 0.0,
    #         "ocf_trend": 0.1763456789,
    #         "dividend_growth_vs_ocf_growth": -0.1763456789,
    #         "sustainability_flag": "CONSERVATIVE GROWTH",
    #     },
    #     {
    #         "bank": "Citigroup",
    #         "year": 2022,
    #         "dividend_per_share": 2.04,
    #         "operating_cash_flow_thousands": 48670000000,
    #         "dividend_yield_trend": 0.0,
    #         "ocf_trend": 0.0760345678,
    #         "dividend_growth_vs_ocf_growth": -0.0760345678,
    #         "sustainability_flag": "CONSERVATIVE GROWTH",
    #     },
    #     {
    #         "bank": "Citigroup",
    #         "year": 2023,
    #         "dividend_per_share": 2.12,
    #         "operating_cash_flow_thousands": 51890000000,
    #         "dividend_yield_trend": 0.0392156863,
    #         "ocf_trend": 0.0661234567,
    #         "dividend_growth_vs_ocf_growth": -0.0269077704,
    #         "sustainability_flag": "CONSERVATIVE GROWTH",
    #     },
    #     {
    #         "bank": "Citigroup",
    #         "year": 2024,
    #         "dividend_per_share": 2.28,
    #         "operating_cash_flow_thousands": 54320000000,
    #         "dividend_yield_trend": 0.0754716981,
    #         "ocf_trend": 0.0468345678,
    #         "dividend_growth_vs_ocf_growth": 0.0286371303,
    #         "sustainability_flag": "MODERATE GROWTH",
    #     },
    # ]

    # if bank:
    #     results = [record for record in results if bank.lower() in record["bank"].lower()]

    return Response({"dividend_sustainability": results})
