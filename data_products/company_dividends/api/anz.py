import requests
from bs4 import BeautifulSoup


def extract_dividends_history(html: str) -> list[dict]:
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


def transform_dividends(dividends: dict) -> dict:
    return {
        "pay_date": dividends["Pay date"],
        "record_date": dividends["Record date"],
        "dividend": dividends["Dividend (AUD)"],
        "franking_level": dividends["Australian Franking level"],
        "imputation_credits": dividends[
            "NZ Imputation\n Credits per\n Ordinary Share\n (NZD)[1]"
        ],
        "drp_price": dividends["DRP price\n (AUD)"],
        "asx_announcement": dividends["ASX announcement"],
    }


def get_dividends() -> list[dict]:
    response = requests.get(
        "https://www.anz.com/shareholder/centre/your-shareholding/dividend-information/"
    )
    raw_dividends_history = extract_dividends_history(response.text)
    dividends_history = [
        transform_dividends(dividends) for dividends in raw_dividends_history
    ]
    return dividends_history
