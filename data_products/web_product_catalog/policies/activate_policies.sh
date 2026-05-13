#!/bin/bash

set -e
cd "$(dirname "$0")" || exit 1

nxd create contract \
  --name web_product_catalog_freshness_contract \
  --code ../contracts/freshness_check.py \
  --description "Freshness check on web-product-catalog: MAX(scraped_at) within 10 hours"

nxd activate policy \
  --name web-product-catalog-freshness \
  --description "Freshness check on web-product-catalog: MAX(scraped_at) within 10 hours" \
  --policy DataQualityCompliance \
  --promise-enforced \
  --validation-url web_product_catalog_freshness_contract \
  --output-ports all \
  --filter '.name == "web-product-catalog"' \
  --env demo \
  --consequence STOP \
  --force-alias-reuse