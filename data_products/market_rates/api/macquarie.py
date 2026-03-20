import requests
from azure.storage.filedatalake import DataLakeFileClient


def sync_term_deposit_data(file_client: DataLakeFileClient):
    response = requests.get(
        "https://www.macquarie.com.au/everyday-banking/term-deposits.csvUpload.html"
    )
    file_client.upload_data(response.text, overwrite=True)


def sync_home_loan_data(file_client: DataLakeFileClient):
    response = requests.get(
        "https://www.macquarie.com.au/home-loans/home-loan-rates.csvUpload.html"
    )
    file_client.upload_data(response.text, overwrite=True)
