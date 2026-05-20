<!-- This table is embedded into our docs. When rendered using docsify, the embed-host value becomes the absolute URL path prefix for
the relative URLs below and the span is not displayed -->
<span class="embed-host" style="display:none">https://github.com/nextdata-tech/nextdata-public-examples/tree/main/data_products/</span>

| Data Product                                                     |       ADLS        | API |    AWS S3    | Databricks | Glossary | MCP | Snowflake |     Spark      |
| ---------------------------------------------------------------- | :---------------: | :-: | :----------: | :--------: | :------: | :-: | :-------: | :------------: |
| [account-coverage](account_coverage/spec.py)                     |                   |     |              |            |          |     |    ✅     |                |
| [company-dividends](company_dividends/spec.py)                   |     ✅ (json)     | ✅  |              |            |          |     |           |                |
| [competitor_growth_analysis](competitor_growth_analysis/spec.py) | ✅ (parquet/json) |     |              |     ✅     |          | ✅  |           |   ✅ (batch)   |
| [credit-card-tx](credit_card_tx/spec.py)                         |   ✅ (parquet)    |     |              |            |          |     |           |                |
| [crm-activity](crm_activity/spec.py)                             |                   |     |              |            |          |     |    ✅     |                |
| [customer-purchases](customer_purchases/spec.py)                 |                   |     | ✅ (parquet) |     ✅     |          |     |           | ✅ (streaming) |
| [engagement-analytics](engagement_analytics/spec.py)             |                   |     |              |            |          |     |    ✅     |                |
| [example-mcp-server](example_mcp/spec.py)                        |                   |     |              |     ✅     |          | ✅  |           |   ✅ (batch)   |
| [financial_statements](financial_statements/spec.py)             |   ✅ (parquet)    | ✅  |              |     ✅     |          | ✅  |           |   ✅ (batch)   |
| [income-statements](income_statements/spec.py)                   |   ✅ (parquet)    | ✅  |              |            |          |     |           |                |
| [loans-products](loans_products/spec.py)                         |                   |     |              |     ✅     |          |     |    ✅     |   ✅ (batch)   |
| [market-announcements](market_announcements/spec.py)             |     ✅ (json)     | ✅  |              |            |          |     |           |                |
| [market-fraud-density](market_fraud_density/spec.py)             |                   | ✅  |   ✅ (CSV)   |            |          |     |           |                |
| [market-rates](market_rates/spec.py)                             |     ✅ (json)     | ✅  |              |            |          |     |           |                |
| [open-meteo-loader](open_meteo_loader/spec.py)                   |                   | ✅  |              |            |          |     |    ✅     |                |
| [product-competitiveness](product_competitiveness/spec.py)       |     ✅ (json)     |     |              |            |          | ✅  |    ✅     |                |
| [public-disclosures](public_disclosures/spec.py)                 |   ✅ (parquet)    |     |              |            |          |     |           |                |
| [retail-catalog-glossary](retail_catalog_glossary/spec.py)       |                   |     |              |            |    ✅    |     |           |                |
| [stock-history](stock_history/spec.py)                           |   ✅ (parquet)    |     |              |     ✅     |          |     |           |                |
| [suspicious-tx](suspicious_tx/spec.py)                           |   ✅ (parquet)    |     |              |            |          |     |           |                |
| [taxi-trip-metrics](taxi-trip-metrics/spec.py)                   |                   |     |              |     ✅     |          |     |           |   ✅ (batch)   |
| [weather-aggregator](weather_aggregator/spec.py)                 |                   |     |              |            |          |     |    ✅     |                |
| [web-product-catalog](web_product_catalog/spec.py)               |                   | ✅  |              |            |          |     |    ✅     |                |
| [wttr-loader](wttr_loader/spec.py)                               |                   | ✅  |              |            |          |     |    ✅     |                |


## ADLS

The Azure Data Lake Storage (ADLS) examples demonstrate how to create a data product that reads from and writes to ADLS.
These examples cover different data formats such as JSON and Parquet, and show how to configure the data product to interact with ADLS using the NextData platform's drivers and connectors.

* [company-dividends](company_dividends/spec.py): A data product that reads company dividend information from an [OFX](https://www.ofx.com) API and writes it to ADLS in JSON format.
* [competitor_growth_analysis](competitor_growth_analysis/spec.py): A data product that reads upstream ADLS datasets, processes competitor analysis outputs, and writes documents (JSON) plus analytics datasets (Parquet) to ADLS.
* [credit-card-tx](credit_card_tx/spec.py): A data product that generates mock credit card transaction data using the [Faker](https://www.geeksforgeeks.org/python/python-faker-library/) library and writes it to ADLS in Parquet format.
* [financial_statements](financial_statements/spec.py): A data product that reads financial statements data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to ADLS in Parquet format. It exposes the output data via an MCP server.
* [income-statements](income_statements/spec.py): A data product that reads income statement data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to ADLS in Parquet format.
* [market-announcements](market_announcements/spec.py): A data product that reads market announcement data via an API and writes it to ADLS in JSON format.
* [market-rates](market_rates/spec.py): A data product that reads market rates data froman [ASX](https://www.asx.com.au/) API and writes it to ADLS in JSON format.
* [product-competitiveness](product_competitiveness/spec.py): A data product that reads product competitiveness data as JSON from ADLS, transforms it via SQL and writes it to Snowflake. The output data is exposed via an MCP server.
* [public-disclosures](public_disclosures/spec.py): A data product that parses public competitor disclosure documents and writes structured representations to ADLS in Parquet format.
* [stock-history](stock_history/spec.py): A data product that reads stock history data via the Yahoo Finance API and writes it to ADLS in Parquet format. The transform runs as python logic on Databricks.
* [suspicious-tx](suspicious_tx/spec.py): A data product that reads the ADLS parquet output of the [credit-card-tx](credit_card_tx/spec.py) data product and writes suspicious transactions to ADLS in Parquet format.

## API

* [company-dividends](company_dividends/spec.py): A data product that reads company dividend information from an [OFX](https://www.ofx.com) API and writes it to ADLS in JSON format.
* [financial_statements](financial_statements/spec.py): A data product that reads financial statements data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to ADLS in Parquet format.
* [income-statements](income_statements/spec.py): A data product that reads income statement data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to ADLS in Parquet format.
* [market-announcements](market_announcements/spec.py): A data product that reads market announcement data via an API and writes it to ADLS in JSON format.
* [market-fraud-density](market_fraud_density/spec.py): A data product that reads [Kaggle](https://www.kaggle.com) bank transaction data using the [Kagglehub](https://github.com/Kaggle/kagglehub) library, generates market fraud density data and writes it to S3 in CSV format. It exposes the output data via an MCP server.
* [market-rates](market_rates/spec.py): A data product that reads market rates data from an [ASX](https://www.asx.com.au/) API and writes it to ADLS in JSON format.
* [open-meteo-loader](open_meteo_loader/spec.py): A data product that ingests current weather conditions from the [Open-Meteo](https://open-meteo.com) public API and writes normalized records into Snowflake.
* [web-product-catalog](web_product_catalog/spec.py): A data product that scrapes paginated HTML product listings from [web-scraping.dev](https://web-scraping.dev/products), enriches them with detail-page data, and writes the catalog to Snowflake.
* [wttr-loader](wttr_loader/spec.py): A data product that ingests current weather conditions from the [wttr.in](https://wttr.in) public API and writes normalized records into Snowflake.

## AWS S3

* [customer_purchases](customer_purchases/spec.py): A data product that reads S3 Parquet data using Spark Streaming on Databricks and writes output to a Databricks table.
* [market-fraud-density](market_fraud_density/spec.py): A data product that reads [Kaggle](https://www.kaggle.com/) bank transaction data using the [Kagglehub](https://github.com/Kaggle/kagglehub) library, generates market fraud density data and writes it to S3 in CSV format. It exposes the output data via an MCP server.

## Databricks

* [competitor_growth_analysis](competitor_growth_analysis/spec.py): A batch data product executed on Databricks that writes growth and dividend sustainability outputs to Databricks tables.
* [customer_purchases](customer_purchases/spec.py): A data product that reads S3 Parquet data using Spark Streaming on Databricks and writes output to a Databricks table.
* [example-mcp-server](example_mcp/spec.py): A data product that generates mock bank data on Databricks and exposes it via an MCP server.
* [financial_statements](financial_statements/spec.py): A data product that reads financial statements data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to both ADLS (Parquet) and Databricks Delta tables. It exposes the output data via an MCP server.
* [loans-products](loans_products/spec.py): A data product that reads product competitiveness data from Snowflake and writes standardized loan datasets to Databricks Unity Catalog tables.
* [stock-history](stock_history/spec.py): A data product that reads stock history data via the Yahoo Finance API and writes it to ADLS in Parquet format. The transform runs as python logic on Databricks.
* [taxi-trip-metrics](taxi-trip-metrics/spec.py): A data product that generates mock taxi trip data using PySpark on Databricks and writes it to a Databricks table.

## MCP

* [competitor_growth_analysis](competitor_growth_analysis/spec.py): A data product that exposes Databricks-backed analysis outputs through MCP RPC functions.
* [example-mcp-server](example_mcp/spec.py): A data product that generates mock bank data on Databricks and exposes it via an MCP server.
* [financial_statements](financial_statements/spec.py): A data product that reads financial statements data from the [Yahoo Finance](https://github.com/ranaroussi/yfinance) API and writes it to ADLS in Parquet format. It exposes the output data via an MCP server.
* [product-competitiveness](product_competitiveness/spec.py): A data product that reads product competitiveness data as JSON from ADLS, transforms it via SQL and writes it to Snowflake. The output data is exposed via an MCP server.

## Snowflake

* [account-coverage](account_coverage/spec.py): A data product that reads the [crm-activity](crm_activity/spec.py) feed from Snowflake and writes per-account coverage and value-gap analysis (realized vs. potential value, touch volume, cost, engagement, coverage classification) to Snowflake. The transform runs as SQL on Snowflake compute, with the coverage logic implemented as a Snowpark Python stored procedure declared and `CALL`ed from `transform.sql`.
* [crm-activity](crm_activity/spec.py): A data product that produces pharmaceutical commercial CRM data — accounts (HCPs/organizations with specialty, value tiering, territory) joined with field activities (calls, details, sample drops, follow-ups, inquiries) — and writes it to Snowflake. The transform runs as SQL on Snowflake compute and exposes custom data-quality promises (orphan activity, invalid NPI, inconsistent casing, inactive accounts with activity, missing email opt-in).
* [engagement-analytics](engagement_analytics/spec.py): A data product that reads the [crm-activity](crm_activity/spec.py) feed from Snowflake and fans out to three analytical models — channel effectiveness and cost-efficiency, monthly engagement trends, and rep/territory scorecards — written back to Snowflake. The transform runs as SQL on Snowflake compute.
* [loans-products](loans_products/spec.py): A data product that reads the output of the [product-competitiveness](product_competitiveness/spec.py) data product from Snowflake and loads curated datasets into Databricks Unity Catalog.
* [open-meteo-loader](open_meteo_loader/spec.py): A data product that ingests current weather conditions from the [Open-Meteo](https://open-meteo.com) public API and writes normalized records into Snowflake.
* [product-competitiveness](product_competitiveness/spec.py): A data product that reads product competitiveness data as JSON from ADLS, transforms it via SQL and writes it to Snowflake. The output data is exposed via an MCP server.
* [weather-aggregator](weather_aggregator/spec.py): A data product that reads from both weather loader outputs and unions them into a unified Snowflake table enriched with provider and process timestamp fields, using Snowpark.
* [web-product-catalog](web_product_catalog/spec.py): A data product that scrapes a competitor retail storefront and writes enriched product catalog records (name, price, brand, description) to Snowflake for competitive pricing analysis.
* [wttr-loader](wttr_loader/spec.py): A data product that ingests current weather conditions from the [wttr.in](https://wttr.in) public API and writes normalized records into Snowflake.

## Glossary

* [retail-catalog-glossary](retail_catalog_glossary/spec.py): A business glossary data product that defines canonical terms for the Retail Catalog domain — including product category, pricing fields, brand, and scrape timestamp — linked from the [web-product-catalog](web_product_catalog/spec.py) semantic model.

## Spark

* [competitor_growth_analysis](competitor_growth_analysis/spec.py): A data product that uses Spark batch transformations on Databricks to compute growth and dividend sustainability models.
* [customer_purchases](customer_purchases/spec.py): A data product that reads S3 Parquet data using Spark Streaming on Databricks and writes output to a Databricks table.
* [example-mcp-server](example_mcp/spec.py): A data product that uses Spark batch transformations on Databricks to generate and write mock bank data to a Delta table.
* [financial_statements](financial_statements/spec.py): A data product that uses Spark batch transformations on Databricks to write `cash_flows` and `balance_sheets` as Delta tables.
* [loans-products](loans_products/spec.py): A data product that uses Spark batch transformations to cast and write loan product models to Delta/Unity Catalog tables.
* [taxi-trip-metrics](taxi-trip-metrics/spec.py): A data product that generates mock taxi trip data using PySpark on Databricks and writes it to a Databricks table.
