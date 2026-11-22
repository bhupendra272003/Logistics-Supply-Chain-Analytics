# Logistics & Supply Chain Analytics

An end-to-end portfolio project for reviewing shipment operations, carrier performance, freight costs and delivery delays.

## Business questions
- How many shipments are delivered, in transit, pending or cancelled?
- Which carriers have the strongest on-time delivery performance?
- How do average freight costs vary by shipping mode?
- How do shipment volumes and delivery delays change over time?
- Which destination regions experience higher average delivery delays?

## Tools
- **Python / pandas:** data type standardization, date parsing, duplicate handling, derived metrics and data-quality flags.
- **SQL / MySQL:** operational aggregations and carrier, mode and regional analysis.
- **Power BI:** KPI cards, shipment trends, carrier comparisons, shipping-mode breakdowns and interactive filters.

## Repository contents
- `clean_data.py` — reproducible Python cleaning pipeline.
- `shipments_raw.csv`, `orders_raw.csv` — source data.
- `carriers.csv`, `locations.csv` — reference data.
- `02_analysis_queries.sql` — example business analysis queries.
- `dashboard.pbix` — Power BI report.
- `dashboard output.png` — dashboard preview.

## Run the cleaning pipeline

Python 3.9+ and pandas are required.

```bash
python -m pip install pandas
python clean_data.py
```

The script supports both the repository's current flat CSV layout and a `data/raw/` layout. It writes cleaned outputs and an audit report to `data/processed/`. Source CSVs are never overwritten.

## Data preparation and quality controls
- Standardizes text fields and parses dates using safe coercion.
- Converts analytical measures to numeric types.
- Removes duplicate shipment and order IDs while recording counts.
- Derives actual transit days and delay days for delivered shipments.
- Flags missing critical shipment identifiers/dates, inconsistent date sequences, negative measures and unfamiliar category values.
- Reports missing-cell counts for each exported table.

Missing measurements are retained as missing rather than fabricated. Review the generated quality report and flagged rows before treating the outputs as operationally ready.

## SQL and dashboard workflow
1. Run the Python cleaning pipeline.
2. Load the processed CSVs into the `logistics_portfolio` MySQL database using the corresponding table names.
3. Execute `02_analysis_queries.sql` after confirming the database and table names.
4. Open `dashboard.pbix` in Power BI Desktop and refresh its data sources if needed.

The SQL examples assume `shipments`, `carriers` and `locations` tables with the fields used in the queries. Confirm the Power BI model's source paths and relationships when opening the PBIX on another machine.

## Validation status
The repository includes the Python pipeline, SQL analysis examples and Power BI file. A live MySQL execution, refresh of the PBIX against the processed outputs, and reconciliation of dashboard figures against SQL results must be completed in the target environment before presenting numerical findings as verified business outcomes.

## Responsible use
This is a portfolio demonstration using sample data, not a production logistics system. Do not use its sample findings to make real operational decisions without validating the source data and business definitions.

---
**Author:** [Bhupendra Singh Deora](https://github.com/bhupendra272003)
