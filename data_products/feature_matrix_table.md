<!-- This table is embedded into our docs. When rendered using docsify, the embed-host value becomes the absolute URL path prefix for
the relative URLs below and the span is not displayed -->
<span class="embed-host" style="display:none">https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/</span>

| Data Product                                               |    ADLS     | API |   AWS S3    | Databricks |  MCP  | Snowflake |     Spark     |
|------------------------------------------------------------|:-----------:|:---:|:-----------:|:----------:|:-----:|:---------:|:-------------:|
| [company-dividends](company_dividends/spec.py)             |  ✅ (json)   |  ✅  |             |            |       |           |               |
| [competitor_growth_analysis](competitor_growth_analysis/manifest.yaml) | ✅ (parquet/json) |     |             |     ✅      |   ✅   |           |   ✅ (batch)   |
| [credit-card-tx](credit_card_tx/spec.py)                   | ✅ (parquet) |     |             |            |       |           |               |
| [customer-purchases](customer_purchases/spec.py)           |             |     | ✅ (parquet) |     ✅      |       |           | ✅ (streaming) |
| [example-mcp-server](example_mcp/spec.py)                  |             |     |             |            |   ✅   |     ✅     |               |
| [financial_statements](financial_statements/spec.py)       | ✅ (parquet) |  ✅  |             |            |   ✅   |           |               |
| [income-statements](income_statements/spec.py)             | ✅ (parquet) |  ✅  |             |            |       |           |               |
| [loans-products](loans_products/spec.py)                   |             |     |             |            |       |     ✅     |               |
| [market-announcements](market_announcements/spec.py)       |  ✅ (json)   |  ✅  |             |            |       |           |               |
| [market-fraud-density](market_fraud_density/spec.py)       |             |  ✅  |   ✅ (CSV)   |            |       |           |               |
| [market-rates](market_rates/spec.py)                       |  ✅ (json)   |  ✅  |             |            |       |           |               |
| [product-competitiveness](product_competitiveness/spec.py) |  ✅ (json)   |     |             |            |   ✅   |     ✅     |               |
| [stock-history](stock_history/spec.py)                     | ✅ (parquet) |     |             |     ✅      |       |           |               |
| [suspicious-tx](suspicious_tx/spec.py)                     | ✅ (parquet) |     |             |            |       |           |               |
| [taxi-trip-metrics](taxi-trip-metrics/spec.py)             |             |     |             |     ✅      |       |           |   ✅ (batch)   |


## ADLS

The Azure Data Lake Storage (ADLS) examples demonstrate how to create a data product that reads from and writes to ADLS.
These examples cover different data formats such as JSON and Parquet, and show how to configure the data product to interact with ADLS using the NextData platform's drivers and connectors.

* [company-dividends](company_dividends/spec.py): A data product that reads company dividend information from an [OFX](https://www.ofx.com) API and writes it to ADLS in JSON format.
* [competitor_growth_analysis](competitor_growth_analysis/manifest.yaml): A data product that reads upstream ADLS datasets, processes competitor analysis outputs, and writes documents (JSON) plus analytics datasets (Parquet) to ADLS.
* [credit-card-tx](credit_card_tx/spec.py): A data product that generates mock credit card transaction data using the [Faker](https://www.geeksforgeeks.org/python/python-faker-library/) library and writes it to ADLS in Parquet format.
* [financial_statements](financial_statements/spec.py): A data product that reads financial statements data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to ADLS in Parquet format. It exposes the output data via an MCP server.
* [income-statements](income_statements/spec.py): A data product that reads income statement data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to ADLS in Parquet format.
* [market-announcements](market_announcements/spec.py): A data product that reads market announcement data via an API and writes it to ADLS in JSON format.
* [market-rates](market_rates/spec.py): A data product that reads market rates data froman [ASX](https://www.asx.com.au/) API and writes it to ADLS in JSON format.
* [product-competitiveness](product_competitiveness/spec.py): A data product that reads product competitiveness data as JSON from ADLS, transforms if via SAL and writes it to Snowflake. The output data is exposed via an MCP server.
* [stock-history](stock_history/spec.py): A data product that reads stock history data via the Yahoo Finance API and writes it to ADLS in Parquet format. The transform runs as python logic on Databricks.
* [suspicious-tx](suspicious_tx/spec.py): A data product that reads the ADLS parquet output of the [credit-card-tx](credit_card_tx/spec.py) data product and writes suspicious transactions to ADLS in Parquet format.
* [product-competitiveness](product_competitiveness/spec.py): A data product that reads product competitiveness data as JSON from ADLS, transforms if via SAL and writes it to Snowflake. It exposes the output data via an MCP server.
  h/nextdata-examples/tree/main/data_products/credit_card_tx/spec.py) data product and writes suspicious transactions to ADLS in Parquet format.

## API

* [company-dividends](company_dividends/spec.py): A data product that reads company dividend information from an [OFX](https://www.ofx.com) API and writes it to ADLS in JSON format.
* [financial_statements](financial_statements/spec.py): A data product that reads financial statements data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to ADLS in Parquet format.
* [income-statements](income_statements/spec.py): A data product that reads income statement data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to ADLS in Parquet format.
* [market-announcements](market_announcements/spec.py): A data product that reads market announcement data via an API and writes it to ADLS in JSON format.
* [market-fraud-density](market_fraud_density/spec.py): A data product that reads [Kaggle](https://www.kaggle.com) bank transaction data using the [Kagglehub](https://github.com/Kaggle/kagglehub) library, generates market fraud density data and writes it to S3 in CSV format. It exposes the output data via an MCP server.
* [market-rates](market_rates/spec.py): A data product that reads market rates data from an [ASX](https://www.asx.com.au/) API and writes it to ADLS in JSON format.

## AWS S3

* [customer_purchases](customer_purchases/spec.py): A data product that reads S3 Parquet data using Spark Streaming on Databricks and writes output to a Databricks table.
* [market-fraud-density](market_fraud_density/spec.py): A data product that reads [Kaggle](https://www.kaggle.com/) bank transaction data using the [Kagglehub](https://github.com/Kaggle/kagglehub) library, generates market fraud density data and writes it to S3 in CSV format. It exposes the output data via an MCP server.

## Databricks

s [competitor_growth_analysis](competitor_growth_analysis/manifest.yaml): A batch data product executed on Databricks that writes growth and dividend sustainability outputs to Databricks tables.
* [customer_purchases](customer_purchases/spec.py): A data product that reads S3 Parquet data using Spark Streaming on Databricks and writes output to a Databricks table.
* [stock-history](stock_history/spec.py): A data product that reads stock history data via the Yahoo Finance API and writes it to ADLS in Parquet format. The transform runs as python logic on Databricks.
* [taxi-trip-metrics](taxi-trip-metrics/spec.py): A data product that generates mock taxi trip data using PySpark on Databricks and writes it to a Databricks table.

## MCP

* [competitor_growth_analysis](competitor_growth_analysis/manifest.yaml): A data product that exposes Databricks-backed analysis outputs through MCP RPC functions.
* [example-mcp-server](example_mcp/spec.py): A data product that demonstrates how to use the MCP server to expose data product output data. It generates mock data in Snowflake and exposes it via an MCP server.
* [financial_statements](financial_statements/spec.py): A data product that reads financial statements data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to ADLS in Parquet format. It exposes the output data via an MCP server.
* [product-competitiveness](product_competitiveness/spec.py): A data product that reads product competitiveness data as JSON from ADLS, transforms if via SAL and writes it to Snowflake. The output data is exposed via an MCP server.

## Snowflake

* [example-mcp-server](example_mcp/spec.py): A data product that demonstrates how to use the MCP server to expose data product output data. It generates mock data in Snowflake and exposes it via an MCP server.
* [loans-products](loans_products/spec.py): A data product that reads the output of the [product-competitiveness](product_competitiveness/spec.py) data product from Snowflake and writes it to Snowflake.
* [product-competitiveness](product_competitiveness/spec.py): A data product that reads product competitiveness data as JSON from ADLS, transforms if via SAL and writes it to Snowflake. The output data is exposed via an MCP server.

## Spark

* [competitor_growth_analysis](competitor_growth_analysis/manifest.yaml): A data product that uses Spark batch transformations on Databricks to compute growth and dividend sustainability models.
* [customer_purchases](customer_purchases/spec.py): A data product that reads S3 Parquet data using Spark Streaming on Databricks and writes output to a Databricks table.
* [taxi-trip-metrics](taxi-trip-metrics/spec.py): A data product that generates mock taxi trip data using PySpark on Databricks and writes it to a Databricks table.