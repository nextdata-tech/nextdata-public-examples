#!/bin/bash
# Deploy contracts and activate DataQualityCompliance policies for the market-fraud-density data product.

set -e
cd "$(dirname "$0")" || exit 1


nxd delete policy --name banksim-transactions-quality || true
nxd delete policy --name fraud-density-quality || true
nxd delete contract --yes banksim_transactions_quality_contract || true
nxd delete contract --yes fraud_density_quality_contract || true

echo "Contracts and policies deleted for market-fraud-density"
