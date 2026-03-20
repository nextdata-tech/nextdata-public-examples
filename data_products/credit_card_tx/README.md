## Policies

### Activation

```
nxd contracts create \
  --name credit_card_tx_pii_compliance_contract \
  --code ./contracts/pii_compliance.py \
  --description "PII Compliance Contract for credit-card-tx - Customers"
```

```
nxd policies activate \
  --name credit-card-tx-pii-compliance \
  --description "PII Compliance Contract for credit-card-tx - Customers" \
  --policy DataQualityCompliance \
  --promise-enforced \
  --validation-url credit_card_tx_pii_compliance_contract \
  --output-ports at-least-one \
  --filter '.name == "credit-card-tx"' \
  --env demo \
  --consequence STOP
```

### Deactivation

```
nxd policies deactivate --name credit-card-tx-pii-compliance
```

### Cleanuo

```
nxd policies delete --name credit-card-tx-pii-compliance
```

```
nxd contracts delete credit_card_tx_pii_compliance_contract
```
