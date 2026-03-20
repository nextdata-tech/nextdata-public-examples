import json

import requests
from azure.storage.filedatalake import DataLakeFileClient


def _get_term_deposits() -> dict:
    response = requests.get("https://www.westpac.com.au/bin/getJsonRates.wbc.td.json")
    json_body = response.json()
    return json_body


def _get_term_deposit_hot_rates() -> dict:
    response = requests.get("https://www.westpac.com.au/bin/getJsonRates.wbc.tdhr.json")
    json_body = response.json()
    return json_body


def _transform_term_deposit(term_deposit: dict) -> dict:
    # HACK: This is required because NXD does not support mixed-case model field names
    rates = next(iter(term_deposit["Rates"].values()))
    return {
        "product_id": term_deposit["ProductId"],
        "status": rates["status"],
        "rate_code": rates["RATECODE"],
        "product": rates["PRODUCT"],
        "min_amount": rates["MinAmt"],
        "max_amount": rates["MaxAmt"],
        "min_term": rates["MinTerm"],
        "max_term": rates["MaxTerm"],
        "maturity_rate": rates.get("Maturityrate"),
        "monthly_rate": rates.get("Monthlyrate"),
        "hot_rate": rates.get("HotRate"),
        "effective_date": rates["EffectiveDate"],
    }


def _get_raw_term_deposits() -> list:
    td = _get_term_deposits()
    td = td["data"]["Brands"]["WBC"]["Portfolios"]["Term Deposits"][
        "Products"
    ]  # fmt: off
    td = list(iter(td.values()))
    term_deposits = [_transform_term_deposit(t) for t in td]

    tdhr = _get_term_deposit_hot_rates()
    tdhr = tdhr["data"]["Brands"]["WBC"]["Portfolios"]["Term Deposit Hot Rates"][
        "Products"
    ]  # fmt: off
    tdhr = list(iter(tdhr.values()))
    term_deposit_hot_rates = [_transform_term_deposit(t) for t in tdhr]

    term_deposits.extend(term_deposit_hot_rates)
    return term_deposits


def sync_term_deposit_data(file_client: DataLakeFileClient):
    term_deposits = _get_raw_term_deposits()
    serialised_term_deposits = json.dumps(term_deposits)
    file_client.upload_data(serialised_term_deposits, overwrite=True)


def _get_lvr3_home_loans():
    response = requests.get(
        "https://www.westpac.com.au/bin/getJsonRates.wbc.hllvr3.json"
    )
    json_body = response.json()
    home_loans = json_body["data"]["Brands"]["WBC"]["Portfolios"][
        "Home Loan LVR3"
    ]  # fmt: off
    return home_loans


def _get_lvr_home_loans():
    response = requests.get("https://www.westpac.com.au/bin/getJsonRates.wbc.hl.json")
    json_body = response.json()
    home_loans = json_body["data"]["Brands"]["WBC"]["Portfolios"][
        "Home Loans"
    ]  # fmt: off
    return home_loans


def _get_lvr5_home_loans():
    response = requests.get(
        "https://www.westpac.com.au/bin/getJsonRates.wbc.hllvr5.json"
    )
    json_body = response.json()
    home_loans = json_body["data"]["Brands"]["WBC"]["Portfolios"][
        "Home Loan LVR5"
    ]  # fmt: off
    return home_loans


def sync_home_loan_data(file_client: DataLakeFileClient):
    lvr3 = _get_lvr3_home_loans()
    lvr = _get_lvr_home_loans()
    lvr5 = _get_lvr5_home_loans()
    products = [lvr3, lvr, lvr5]
    serialised_home_loans = "\n".join([json.dumps(product) for product in products])
    file_client.upload_data(serialised_home_loans, overwrite=True)


if __name__ == "__main__":
    sync_home_loan_data()
