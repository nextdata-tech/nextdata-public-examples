# nextdata-public-examples

A collection of example [Nextdata](https://nextdata.com) data products demonstrating how to build data products across
a variety of infrastructure targets and real-world use cases.

These examples are intended to help you understand how to use the NextData platform — from simple batch transforms to
streaming pipelines, MCP servers, and data quality contracts.

## Data Products

Each data product lives in its own directory under [`data_products/`](./data_products) and contains a
specification (`spec.py`), a transform (`transform.py`), data models (`models.py`), and any supporting contracts or expectations.

## Feature Matrix

This [data_products/feature_matrix_table.md](data_products/feature_matrix_table.md) table shows which infrastructure targets and capabilities each data product uses.

## Getting Started

Each data product directory contains a `requirements.txt` with its dependencies. Refer to the individual `spec.py` for
the infrastructure profile and trigger configuration, and `transform.py` for the data processing logic.
