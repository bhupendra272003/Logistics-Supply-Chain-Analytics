from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

def standardize_text(series):
    return series.astype("string").str.strip()

def main():
    shipments = pd.read_csv(RAW / "shipments_raw.csv")
    orders = pd.read_csv(RAW / "orders_raw.csv")
    carriers = pd.read_csv(RAW / "carriers.csv")
    locations = pd.read_csv(RAW / "locations.csv")

    before_shipments = len(shipments)
    before_orders = len(orders)

    # Standardise identifiers and categorical text.
    for col in ["shipment_id", "order_id", "origin_location_id",
                "destination_location_id", "carrier_id", "shipment_status"]:
        shipments[col] = standardize_text(shipments[col])
    shipments["shipping_mode"] = standardize_text(shipments["shipping_mode"]).str.title()
    shipments["shipment_status"] = standardize_text(shipments["shipment_status"]).str.title()
    orders["product_category"] = standardize_text(orders["product_category"]).str.title()
    orders["priority"] = standardize_text(orders["priority"]).str.title()

    # Parse dates and numeric columns.
    for col in ["order_date", "dispatch_date", "delivery_date"]:
        shipments[col] = pd.to_date(shipments[col], errors="coerce")
    for col in ["distance_km", "weight_kg", "freight_cost_inr", "promised_delivery_days"]:
        shipments[col] = pd.to_numeric(shipments[col], errors="coerce")
    for col in ["quantity", "order_value_inr"]:
        orders[col] = pd.to_numeric(orders[col], errors="coerce")

    # Normalize expected categories.
    mode_map = {"Road": "Road", "Air": "Air", "Rail": "Rail"}
    shipments["shipping_mode"] = shipments["shipping_mode"].map(mode_map)

    # Create a duplicate audit before deduplication.
    duplicate_shipments = int(shipments.duplicated(subset=["shipment_id"], keep="first").sum())
    duplicate_orders = int(orders.duplicated(subset=["order_id"], keep="first").sum())

    shipments = shipments.drop_duplicates(subset=["shipment_id"], keep="first")
    orders = orders.drop_duplicates(subset=["order_id"], keep="first")

    # Flag missing critical keys instead of silently fabricating replacements.
    shipments["data_quality_issue"] = (
        shipments["origin_location_id"].isna()
        | shipments["origin_location_id"].eq("")
        | shipments["destination_location_id"].isna()
        | shipments["destination_location_id"].eq("")
        | shipments["carrier_id"].isna()
        | shipments["carrier_id"].eq("")
        | shipments["dispatch_date"].isna()
    )

    # Transit days only for valid delivered shipments.
    shipments["actual_transit_days"] = (
        shipments["delivery_date"] - shipments["dispatch_date"]
    ).dt.days
    shipments.loc[shipments["actual_transit_days"] < 0, "data_quality_issue"] = True
    shipments["delay_days"] = (
        shipments["actual_transit_days"] - shipments["promised_delivery_days"]
    ).clip(lower=0)
    shipments.loc[shipments["shipment_status"].ne("Delivered"), "delay_days"] = pd.NA

    # Save cleaned tables. Missing measurements remain missing; don't invent values.
    shipments.to_csv(OUT / "shipments_clean.csv", index=False, date_format="%Y-%m-%d")
    orders.to_csv(OUT / "orders_clean.csv", index=False)
    carriers.to_csv(OUT / "carriers_clean.csv", index=False)
    locations.to_csv(OUT / "locations_clean.csv", index=False)

    report = [
        "DATA CLEANING REPORT",
        "====================",
        f"Shipments raw rows: {before_shipments}",
        f"Shipments unique rows after dedupe: {len(shipments)}",
        f"Duplicate shipment IDs removed: {duplicate_shipments}",
        f"Orders raw rows: {before_orders}",
        f"Orders unique rows after dedupe: {len(orders)}",
        f"Duplicate order IDs removed: {duplicate_orders}",
        f"Shipments flagged for key/date quality review: {int(shipments['data_quality_issue'].sum())}",
        f"Missing weight_kg after cleaning: {int(shipments['weight_kg'].isna().sum())}",
        f"Missing freight_cost_inr after cleaning: {int(shipments['freight_cost_inr'].isna().sum())}",
        "",
        "Review these outputs before treating the data as analysis-ready:",
        "- data/processed/shipments_clean.csv",
        "- data/processed/orders_clean.csv",
        "- data/processed/carriers_clean.csv",
        "- data/processed/locations_clean.csv",
    ]
    (OUT / "cleaning_report.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))

if __name__ == "__main__":
    main()
