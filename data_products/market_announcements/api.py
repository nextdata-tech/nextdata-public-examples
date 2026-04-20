import csv
from datetime import date
from datetime import datetime
from io import BytesIO
from io import StringIO

import requests
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class Company(BaseModel):
    asx_code: str = Field(validation_alias="ASX code")
    company_name: str = Field(validation_alias="Company name")
    gics_industry_group: str = Field(validation_alias="GICs industry group")
    listing_date: date = Field(validation_alias="Listing date")
    market_cap: str = Field(validation_alias="Market Cap")

    @field_validator("listing_date", mode="before")
    @classmethod
    def validate_listing_date(cls, value: date | str) -> date:
        if isinstance(value, date):
            return value
        return datetime.strptime(value, "%d/%m/%Y").date()


class AnnouncementCompanies(BaseModel):
    symbol_display: str = Field(validation_alias="symbolDisplay")


class AnnouncementCompanyInfo(BaseModel):
    symbol: str
    xid: str
    asx_security_type: int = Field(validation_alias="ASXSecurityType")
    display_name: str = Field(validation_alias="displayName")
    issue_type: str | None = Field(validation_alias="issueType", default=None)
    issue_type_name: str | None = Field(validation_alias="issueTypeName", default=None)
    issue_type_code: int = Field(validation_alias="issueTypeCode")
    isin: str | None = None
    xid_entity: int | None = Field(validation_alias="xidEntity", default=None)
    sector: str | None = None
    industry_group: str | None = Field(validation_alias="industryGroup", default=None)
    industry: str | None = None
    sub_industry: str | None = Field(validation_alias="subIndustry", default=None)


class Announcement(BaseModel):
    annoucement_types: list[str] = Field(validation_alias="announcementTypes")
    companies: list[AnnouncementCompanies]
    company_info: list[AnnouncementCompanyInfo] = Field(validation_alias="companyInfo")
    date: datetime
    document_key: str = Field(validation_alias="documentKey")
    file_size: str = Field(validation_alias="fileSize")
    headline: str
    is_price_sensitive: bool = Field(validation_alias="isPriceSensitive")
    symbol: str
    symbols_secondary: list[str] = Field(validation_alias="symbolsSecondary")
    url: str


class ASXMarkitDigital:
    base_url = "https://asx.api.markitdigital.com/asx-research/1.0"

    def get_companies_directory_file(self) -> list[Company]:
        r = requests.get(
            url=f"{self.base_url}/companies/directory/file",
            headers={"Accept": "text/csv"},
        )
        reader = csv.DictReader(StringIO(r.text))
        return [Company.model_validate(row) for row in reader]

    def get_markets_announcements(
        self,
        xids: list[str],
        date_start: date,
        items_per_page: int = 10000,
        price_sensitive_only: bool = True,
    ) -> list[Announcement]:
        r = requests.get(
            url=f"{self.base_url}/markets/announcements",
            headers={"Accept": "application/json"},
            params={
                "dateStart": str(date_start),
                "itemsPerPage": items_per_page,
                "priceSensitiveOnly": str(price_sensitive_only).lower(),
                "xids": ",".join(xids),
            },
        )

        announcements = [Announcement.model_validate(row) for row in r.json()["data"]["items"]]

        return announcements

    def get_file(self, document_key: str) -> BytesIO:
        r = requests.get(
            url=f"{self.base_url}/file/{document_key}",
            headers={"Accept": "application/pdf"},
        )

        return BytesIO(r.content)
