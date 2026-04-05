
# Financial statements


```bash
# Register a contract with code file
nxd contracts create \
  --name pii-rag \
  --code ./validations.py \
  --description "PII RAG validation contract"

```


```bash
# Activate the policy
nxd policies activate \
  --name pii_rag_for_financial_statements \
  --description "PII for financial statements" \
  --policy DataQualityCompliance \
  --promise-enforced \
  --validation-url pii-rag \
  --output-ports at-least-one \
  --filter '.name == "financial-statements"' \
  --env demo \
  --consequence STOP
```
## Clean up

```bash
nxd contracts delete pii-rag
```

```bash
nxd policies delete --name pii_rag_for_financial_statements
```

## Model metrics reference

### `balance_sheets`

- treasury_shares_number
- ordinary_shares_number
- share_issued
- net_debt
- total_debt
- tangible_book_value
- invested_capital
- net_tangible_assets
- common_stock_equity
- total_capitalization
- total_equity_gross_minority_interest
- minority_interest
- stockholders_equity
- gains_losses_not_affecting_retained_earnings
- treasury_stock
- retained_earnings
- capital_stock
- common_stock
- total_liabilities_net_minority_interest
- derivative_product_liabilities
- non_current_deferred_liabilities
- non_current_deferred_taxes_liabilities
- long_term_debt_and_capital_lease_obligation
- long_term_debt
- long_term_provisions
- current_debt_and_capital_lease_obligation
- current_debt
- commercial_paper
- payables_and_accrued_expenses
- payables
- total_tax_payable
- income_tax_payable
- accounts_payable
- total_assets
- investments_and_advances
- available_for_sale_securities
- trading_securities
- long_term_equity_investment
- goodwill_and_other_intangible_assets
- other_intangible_assets
- goodwill
- net_ppe
- receivables
- other_receivables
- accounts_receivable
- other_short_term_investments
- cash_and_cash_equivalents
- cash_financial
- cash_cash_equivalents_and_federal_funds_sold
- other_payable
- investmentin_financial_assets
- financial_assets_designatedas_fair_value_through_profitor_loss_total
- investments_in_other_ventures_under_equity_method
- investmentsin_associatesat_cost
- taxes_receivable

### `cash_flows`

- free_cash_flow
- repurchase_of_capital_stock
- repayment_of_debt
- issuance_of_debt
- issuance_of_capital_stock
- capital_expenditure
- end_cash_position
- other_cash_adjustment_outside_changein_cash
- beginning_cash_position
- effect_of_exchange_rate_changes
- changes_in_cash
- financing_cash_flow
- cash_flow_from_continuing_financing_activities
- net_other_financing_charges
- proceeds_from_stock_option_exercised
- cash_dividends_paid
- common_stock_dividend_paid
- net_common_stock_issuance
- common_stock_payments
- common_stock_issuance
- net_issuance_payments_of_debt
- net_long_term_debt_issuance
- long_term_debt_payments
- long_term_debt_issuance
- investing_cash_flow
- cash_flow_from_continuing_investing_activities
- net_investment_purchase_and_sale
- sale_of_investment
- purchase_of_investment
- net_business_purchase_and_sale
- sale_of_business
- purchase_of_business
- net_intangibles_purchase_and_sale
- purchase_of_intangibles
- net_ppe_purchase_and_sale
- sale_of_ppe
- purchase_of_ppe
- operating_cash_flow
- cash_flow_from_continuing_operating_activities
- change_in_working_capital
- change_in_other_working_capital
- change_in_other_current_liabilities
- change_in_other_current_assets
- change_in_payables_and_accrued_expense
- change_in_payable
- change_in_account_payable
- change_in_receivables
- changes_in_account_receivables
- other_non_cash_items
- deferred_tax
- deferred_income_tax
- depreciation_amortization_depletion
- depreciation_and_amortization
- net_income_from_continuing_operations
- net_preferred_stock_issuance
- preferred_stock_issuance
- provisionand_write_offof_assets
- depreciation
- gain_loss_on_investment_securities
- gain_loss_on_sale_of_ppe
- gain_loss_on_sale_of_business
