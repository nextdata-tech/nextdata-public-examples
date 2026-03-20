
# Market Rates


## Example Data Product

### Term Deposits
- URL: https://www.westpac.com.au/personal-banking/bank-accounts/term-deposit/
- Rate minimum: $5,000
- Rate maximum: $2,000,000
- Interest varies based on whether it’s paid out monthly or at maturity. Interest paid monthly is lower than at maturity
- The online calculator is feed using a JSON API backend which can be used to fetch current rates:
    - [Standard Rates](https://www.westpac.com.au/bin/getJsonRates.wbc.td.json): [rates-td.json](rates-td.json)
    - [Hot Rates](https://www.westpac.com.au/bin/getJsonRates.wbc.tdhr.json): [rates-tdhr.json](rates-tdhr.json)
- Entries look like this:


```json
{
    "Term Deposit - 10000~0.25": {
        "ProductId": "TermDeposit-10000~0.25",
        "Rates": {
            "10000~0.25": {
                "status": "PUBLISHED",
                "RATECODE": "10000~0.25",
                "PRODUCT": "Term Deposit - 10000~0.25å",
                "MinAmt": "10000",
                "MaxAmt": "20000",
                "MinTerm": "0.25",
                "MaxTerm": "1",
                "Maturityrate": "1.25",
                "Colour(maturity)": "black",
                "Monthlyrate": "1.25",
                "Colour(monthly)": "black",
                "HotRate": "",
                "EffectiveDate": "12/05/2023"
            }
        }
    }
}

```

### Home Loans
- https://www.westpac.com.au/personal-banking/home-loans/calculator/mortgage-repayment/
- Vary based on:
    - Buy/Refiance
    - First Property/Investment Property
    - Interest/Principal & Interest
    - LVR (0.1% discount if 70% LVR, 70-80% is normal, 80%+ is a 0.3% mark up)
    - Fixed
    - Package and bundling (Premier Advntage Package): Must have a Westpac transaction account.
- 3 options for loan type:
    - Basic Variable (Floating rate)
    - Fixed Options package (fixed)
    - Rocket Repay (Offset)



```json
{
    "Rocket Home Loan Premier Advantage $150k-$250k": {
        "ProductId": "RocketHomeLoanPremierAdvantage$150k-$250k",
        "Rates": {
            "PAHLRR150": {
                "status": "PUBLISHED",
                "RATECODE": "PAHLRR150",
                "PRODUCT": "Rocket Home Loan Premier Advantage $150k-$250k",
                "Term": "25",
                "Loan_Amount": "150000",
                "Std_Rate": "5.89",
                "Std_MCR": "6.27",
                "Std_discount": "2.34",
                "Std_Effective_date": "",
                "Std_Applies_from_date": "",
                "Std_Conditionally_approved_by_date": "",
                "Spl_1_Rate": "",
                "Spl_1_MCR": "",
                "Spl_1_discount": "",
                "Spl_1_Effective_date": "",
                "Spl_1_Applies_from_date": "",
                "Spl_1_Conditionally_approved_by_date": "",
                "Spl_3_Rate": "",
                "Spl_3_MCR": "",
                "Spl_3_discount": "",
                "Spl_3_Effective_date": "",
                "Spl_3_Applies_from_date": "",
                "Spl_3_Conditionally_approved_by_date": ""
            }
        }
    },
    "Rocket Home Loan Premier Advantage $1mil+": {
        "ProductId": "RocketHomeLoanPremierAdvantage$1mil+",
        "Rates": {
            "PAHLRR10001": {
                "status": "PUBLISHED",
                "RATECODE": "PAHLRR10001",
                "PRODUCT": "Rocket Home Loan Premier Advantage $1mil+",
                "Term": "25",
                "Loan_Amount": "150000",
                "Std_Rate": "5.89",
                "Std_MCR": "6.27",
                "Std_discount": "2.34",
                "Std_Effective_date": "",
                "Std_Applies_from_date": "",
                "Std_Conditionally_approved_by_date": "",
                "Spl_1_Rate": "",
                "Spl_1_MCR": "",
                "Spl_1_discount": "",
                "Spl_1_Effective_date": "",
                "Spl_1_Applies_from_date": "",
                "Spl_1_Conditionally_approved_by_date": "",
                "Spl_3_Rate": "",
                "Spl_3_MCR": "",
                "Spl_3_discount": "",
                "Spl_3_Effective_date": "",
                "Spl_3_Applies_from_date": "",
                "Spl_3_Conditionally_approved_by_date": ""
            }
        }
    }
}
```

---

## ANZ

### Term Deposit

- URL: https://www.anz.com.au/personal/bank-accounts/term-deposits
- At first glance, seems to be the simplest. They have one type of term deposit "ANZ Advance Notice Term Deposit"
- URL: https://www.anz.com.au/personal/bank-accounts/term-deposits/advance-notice/
- Rates are available in an ASP response from: https://www.anz.com/productdata/productdata.asp?output=json&callback=callbackFunction&country=AU&section=PDA&subsection=&_=1755038465630
- Offer interest at maturity, monthly, half-yearly or annual
- $5000-$2,000,000

### Home Loan

- URL: https://www.anz.com.au/personal/home-loans/interest-rates
- Rates available at: https://www.anz.com/productdata/productdata.asp?country=AU&section=PRL&output=JSON&callback=asyncCallbackFunction&_=1755052624853
- Offers an "Index rate" home loan which isn't directly comparable to Westpac

---

## Macquarie

### Term Deposit
- URL: https://www.macquarie.com.au/everyday-banking/term-deposits.html
- Data is available in a *structured* shape at a URL: https://www.macquarie.com.au/everyday-banking/term-deposits.csvUpload.html
- Interest can be out at maturity, monthly, quarterly and annually (where applicable)

### Home Loan

- URL: https://www.macquarie.com.au/home-loans/home-loan-rates.html
- Available as JSON: https://www.macquarie.com.au/home-loans/home-loan-rates.csvUpload.html


## Semantic Models

### Home Loans

- Westpac has 3 essential loan products:
    - Floating home loan. (Flexi First Option Home Loan)
    - Fixed home loan. (Fixed Options Home Loan – package#)
    - Floating with Offset. (Rocket Repay Home Loan – package#)
- Loans vary based on:
    - LVR
    - Loan type
    - Interest Only/Interest + Principal

schema:
- bank: str
- product: str
- interest_only: bool
- loan_type: str (FLOATING, FIXED, OFFSET)
- loan_term: int (1, 2, 3, 4, 5)
- lvr: int
- rate: decimal(6, 2)
