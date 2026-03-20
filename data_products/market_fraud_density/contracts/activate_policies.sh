#!/bin/bash
# Deploy contracts and activate DataQualityCompliance policies for the market-fraud-density data product.

set -e
cd "$(dirname "$0")" || exit 1

# Delete stale policies 

nxd policies delete --name banksim-transactions-quality || true
nxd policies delete --name fraud-density-quality || true

# Register contracts

nxd contracts create \
  --name banksim_transactions_quality_contract \
  --code ./banksim_transactions_quality.py \
  --description "Zero-Null check on category/fraud + non-negative amount for the raw BankSim1 transactions model"

nxd contracts create \
  --name fraud_density_quality_contract \
  --code ./fraud_density_quality.py \
  --description "Uniqueness of market_type, fraud_rate_pct in [0-100], transaction_count > 0 for the fraud density model"

# Activate policies

nxd policies activate \
  --name banksim-transactions-quality \
  --description "Zero-Null check on category/fraud + non-negative amount for BankSim1 transactions" \
  --policy DataQualityCompliance \
  --promise-enforced \
  --validation-url banksim_transactions_quality_contract \
  --output-ports all \
  --filter '.name == "market-fraud-density"' \
  --env demo \
  --consequence STOP \
  --force-alias-reuse

nxd policies activate \
  --name fraud-density-quality \
  --description "Validates uniqueness of market_type, fraud_rate_pct range and transaction_count for fraud density model" \
  --policy DataQualityCompliance \
  --promise-enforced \
  --validation-url fraud_density_quality_contract \
  --output-ports all \
  --filter '.name == "market-fraud-density"' \
  --env demo \
  --consequence STOP \
  --force-alias-reuse

echo "Contracts registered and policies activated for market-fraud-density"
