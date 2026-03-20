import logging

import requests
from bs4 import BeautifulSoup

_logger = logging.getLogger("api.anz")
_logger.setLevel(logging.INFO)


def extract_macquarie_dividends_history(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    # HACK: The second table contains the dividends history we are interested in
    table = soup.find_all("table")[1]
    headers = [th.text for th in table.find_all("th")]
    # HACK: First row has nothing in it
    rows = [tuple(td.text for td in tr.find_all("td")) for tr in table.find_all("tr")][
        1:
    ]  # fmt: off
    dividends_history = [dict(zip(headers, row)) for row in rows]
    return dividends_history


def transform_dividends_history(dividend: dict) -> dict:
    return {
        "divident": dividend["Dividend"],
        "divident_per_share": dividend["Dividends per fully paid ordinary share (AU cents)"],
        "franked_amount": dividend["Franked amount"],
        "ranked_amount_tax_rate": dividend["Applicable tax rate for franked amounts"],
        "record_date": dividend["Record date (dd/mm/yy)"],
        "payment_date": dividend["Payment date (dd/mm/yy)"],
    }


def get_dividends() -> list[dict]:
    response = requests.get("https://www.macquarie.com/nz/en/investors/dividends.html")
    raw_dividends_history = extract_macquarie_dividends_history(response.text)
    dividends_history = [transform_dividends_history(dividend) for dividend in raw_dividends_history]
    return dividends_history
