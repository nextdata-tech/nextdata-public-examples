# Merchant-Fraud-Insights
### 1. User requirements

- **1:** The product must provide a consolidated view of fraud density across different merchant categories (Market Types).
- **2:** Risk analysts must be able to identify which markets have the highest volume of fraud versus the highest percentage of fraud (relative risk).
- **3:** The data must be cleaned of "ES" (Enterprise/Simulation) artifacts and represent normalized merchant categories.
- 4: The product must simulate a streaming data environment by fetching and processing data from the Kaggle API in scheduled periodic batches.
- 5. The system must expose a dedicated API endpoint that allows the data to be consumed directly by a Power BI dashboard and an AI-driven agentic application.
### 2. Acceptance criteria

- **1:** The output must contain exactly one row per unique merchant category.
- **2:** The `fraud_percentage` must be calculated as `(total_fraud_events / total_transactions) * 100`.
- **3:** Any category with zero transactions must not appear in the final output.
- **4:** Data must pass a "Zero Null" expectation check for the `category` and `fraud` fields before being published.

### 3. Data product definition (NextData OS pattern)

#### A. Input (The Source)
The input is the raw BankSim1 transaction stream/table.
- **Source:** `banksim_raw_transactions`
- **Key Fields Used:**
    - `category`: The merchant category (Market Type).
    - `fraud`: Binary indicator (1 for fraud, 0 for legitimate).

#### B. The Model (Logical Schema)
This is the "Data Contract" that the consumer sees.

| **Field Name**      | **Data Type** | **Description**                                               |
| ------------------- | ------------- | ------------------------------------------------------------- |
| `market_type`       | STRING        | The merchant category (e.g., 'es_transportation', 'es_food'). |
| `transaction_count` | INTEGER       | Total number of transactions recorded for this market.        |
| `fraud_event_count` | INTEGER       | Total number of confirmed fraudulent transactions.            |
| `fraud_rate_pct`    | FLOAT         | The percentage of transactions that were fraudulent.          |

#### C. Outputs (Consumption Points)
Following the "Data Mesh" approach, this product provides two ports:
1. **SQL Output:** A materialized view or table in your data warehouse (BigQuery/Snowflake/Databricks) for dashboarding.
2. **API Output:** A REST endpoint or GraphQL query for the "Agentic Application" to fetch real-time stats.

---

### 4. Expectations & promises

#### Data expectations (internal quality)
- **Uniqueness:** `market_type` must be the Primary Key (no duplicates).
- **Range Check:** `fraud_rate_pct` must be between `0.0` and `100.0`.
- **Completeness:** `transaction_count` must always be greater than 0.

#### Data promises
- **Freshness:** The data is updated every 24 hours (Batch) or based on the latest streaming ETL window.
- **Governance:** This data product is compliant with financial auditing standards (no PII included).

---

### 5. Implementation logic (the transformation)

To implement the "Model" defined above, the logic will follow this structure:

SQL

```
SELECT 
    category AS market_type,
    COUNT(*) AS transaction_count,
    SUM(fraud) AS fraud_event_count,
    ROUND((SUM(fraud) * 100.0 / COUNT(*)), 2) AS fraud_rate_pct
FROM 
    `source_banksim_data`
GROUP BY 
    1
ORDER BY 
    fraud_rate_pct DESC;
```
