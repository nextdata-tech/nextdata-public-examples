nxd delete contract \
  web_product_catalog_freshness_contract \
  -y || true

nxd deactivate policy \
  --name web-product-catalog-freshness || true

nxd delete policy \
  --name web-product-catalog-freshness || true