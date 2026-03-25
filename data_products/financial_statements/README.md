
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
