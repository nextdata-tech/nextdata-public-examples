import requests
from bs4 import BeautifulSoup


def extract_dividends_history(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    # HACK: The second table contains the dividends history we are interested in
    table = soup.find("table")
    headers = [th.text for th in table.find_all("th")]
    # HACK: First and second do not contain data of interest
    rows = [tuple(td.text for td in tr.find_all("td")) for tr in table.find_all("tr")][
        2:
    ]  # fmt: off
    dividends_history = [dict(zip(headers, row)) for row in rows]
    return dividends_history


def transform_dividends(dividends: dict) -> dict:
    # HACK: This is required because NXD does not support mixed-case model field names
    return {
        "payment_date": dividends["Payment date"],
        "rate": dividends["Rate (cents)"],
        "franking_level": dividends["Franking level\xa0"],
        "nz_imputation_credits": dividends["New Zealand imputation credits"],
        "share_price": dividends["DRP*\xa0"],
        "divident_bonus_plan": dividends["DBP**\xa0"],
    }


def get_dividends() -> list[dict]:
    response = requests.get(
        "https://www.westpac.com.au/about-westpac/investor-centre/dividend-information/dividend-payment-history/"
    )
    raw_dividends_history = extract_dividends_history(response.text)
    dividends_history = [
        transform_dividends(dividends) for dividends in raw_dividends_history
    ]
    return dividends_history
