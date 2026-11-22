"""Clean and validate the logistics portfolio CSV files.

Supports both the repository's current flat layout and data/raw layout.
Raw inputs are never modified. Cleaned outputs and an audit report are written
to data/processed/.
"""
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

REQUIRED_COLUMNS = {
    "shipments": [
        "shipment_id", "order_id", "order_date", "dispatch_date", "delivery_date",
        "origin_location_id", "destination_location_id", "carrier_id", "shipping_mode",
        "distance_km", "weight_kg", "freight_cost_inr", "promised_delivery_days",
        "shipment_status",
    ],
    "orders": ["order_id", "product_category", "quantity", "order_value_inr", "priority"],
    "carriers": ["carrier_id", "carrier_name"],
    "locations": ["location_id", "region"],
}


def locate_input(filename: str) -> Path:
    """Prefer data/raw, then data, then repository root for backward compatibility."""
    candidates = [
        PROJECT_ROOT / "data" / "raw" / filename,
        PROJECT_ROOT / "data" / filename,
        PROJECT_ROOT / filename,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    searched = "\n".join(f"- {p}" for p in candidates)
    raise FileNotFoundError(f"Could not find {filename}. Checked:\n{searched}")


def read_csv(name: str) -> pd.DataFrame:
    path = locate_input(name)
    frame = pd.read_csv(path)
    frame.columns = frame.columns.str.strip()
    missing = sorted(set(REQUIRED_COLUMNS[name]) - set(frame.columns))
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {', '.join(missing)}")
    return frame


def standardize_text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().replace({"": pd.NA})


def main() -> None:
    shipments = read_csv("shipments").copy()
    orders = read_csv("orders").copy()
    carriers = read_csv("carriers").copy()
    locations = read_csv("locations").copy()

    raw_shipments, raw_orders = len(shipments), len(orders)

    # Standardize text consistently; preserve unfamiliar categories for review.
    text_columns = [
        "shipment_id", "order_id", "origin_location_id", "destination_location_id",
        "carrier_id", "shipment_status", "shipping_mode",
    ]
    for column in text_columns:
        shipments[column] = standardize_text(shipments[column])
    for column in ("product_category", "priority"):
        orders[column] = standardize_text(orders[column])
    for column in ("carrier_id", "carrier_name"):
        carriers[column] = standardize_text(carriers[column])
    for column in ("location_id", "region"):
        locations[column] = standardize_text(locations[column])

    shipments["shipping_mode"] = shipments["shipping_mode"].str.title()
    shipments["shipment_status"] = shipments["shipment_status"].str.title()
    orders["product_category"] = orders["product_category"].str.title()
    orders["priority"] = orders["priority"].str.title()

    # Parse dates safely. Invalid or missing values remain null and are reported.
    date_columns = ("order_date", "dispatch_date", "delivery_date")
    for column in date_columns:
        shipments[column] = pd.to_datetime(shipments[column], errors="coerce")

    numeric_shipment_columns = (
        "distance_km", "weight_kg", "freight_cost_inr", "promised_delivery_days"
    )
    for column in numeric_shipment_columns:
        shipments[column] = pd.to_numeric(shipments[column], errors="coerce")
    for column in ("quantity", "order_value_inr"):
        orders[column] = pd.to_numeric(orders[column], errors="coerce")

    # Capture duplicate counts before keeping the first occurrence of each key.
    duplicate_shipments = int(shipments.duplicated(subset=["shipment_id"], keep="first").sum())
    duplicate_orders = int(orders.duplicated(subset=["order_id"], keep="first").sum())
    shipments = shipments.drop_duplicates(subset=["shipment_id"], keep="first").copy()
    orders = orders.drop_duplicates(subset=["order_id"], keep="first").copy()

    # Derived operational measures.
    shipments["actual_transit_days"] = (
        shipments["delivery_date"] - shipments["dispatch_date"]
    ).dt.days
    invalid_date_sequence = (
        shipments["dispatch_date"].lt(shipments["order_date"])
        | shipments["delivery_date"].lt(shipments["dispatch_date"])
    )
    negative_metrics = (
        shipments[list(numeric_shipment_columns)].lt(0).any(axis=1)
        | orders[["quantity", "order_value_inr"]].lt(0).any(axis=1).reindex(
            shipments.index, fill_value=False
        )
    )
    # Delay is meaningful only for delivered shipments with valid duration and promise.
    valid_delay = (
        shipments["shipment_status"].eq("Delivered")
        & shipments["actual_transit_days"].notna()
        & shipments["promised_delivery_days"].notna()
    )
    shipments["delay_days"] = pd.Series(pd.NA, index=shipments.index, dtype="Int64")
    delay_values = (
        shipments.loc[valid_delay, "actual_transit_days"]
        - shipments.loc[valid_delay, "promised_delivery_days"]
    ).clip(lower=0)
    shipments.loc[valid_delay, "delay_days"] = delay_values.astype("Int64")

    known_modes = {"Road", "Air", "Rail"}
    known_statuses = {"Delivered", "In Transit", "Pending", "Cancelled"}
    missing_key_or_date = (
        shipments[["shipment_id", "order_id", "origin_location_id",
                   "destination_location_id", "carrier_id"]].isna().any(axis=1)
        | shipments["dispatch_date"].isna()
    )
    unknown_category = (
        ~shipments["shipping_mode"].isin(known_modes)
        | ~shipments["shipment_status"].isin(known_statuses)
    )
    shipments["data_quality_issue"] = (
        missing_key_or_date | invalid_date_sequence | negative_metrics | unknown_category
    )

    # Export clean snapshots; source CSVs stay untouched.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shipments.to_csv(OUTPUT_DIR / "shipments_clean.csv", index=False, date_format="%Y-%m-%d")
    orders.to_csv(OUTPUT_DIR / "orders_clean.csv", index=False)
    carriers.to_csv(OUTPUT_DIR / "carriers_clean.csv", index=False)
    locations.to_csv(OUTPUT_DIR / "locations_clean.csv", index=False)

    report = [
        "LOGISTICS DATA CLEANING & QUALITY REPORT",
        "=" * 42,
        f"Shipments raw rows: {raw_shipments:,}",
        f"Shipments unique rows: {len(shipments):,}",
        f"Duplicate shipment IDs removed: {duplicate_shipments:,}",
        f"Orders raw rows: {raw_orders:,}",
        f"Orders unique rows: {len(orders):,}",
        f"Duplicate order IDs removed: {duplicate_orders:,}",
        f"Shipments flagged for quality review: {int(shipments['data_quality_issue'].sum()):,}",
        f"Invalid or inconsistent date sequences: {int(invalid_date_sequence.sum()):,}",
        f"Rows with missing critical shipment keys/dates: {int(missing_key_or_date.sum()):,}",
        f"Rows with unknown shipment category values: {int(unknown_category.sum()):,}",
        "",
        "Remaining missing values by output:",
    ]
    for name, frame in (
        ("shipments_clean.csv", shipments),
        ("orders_clean.csv", orders),
        ("carriers_clean.csv", carriers),
        ("locations_clean.csv", locations),
    ):
        missing = int(frame.isna().sum().sum())
        report.append(f"- {name}: {missing:,} missing cells")
    report.extend([
        "",
        "Outputs: data/processed/",
        "Review data_quality_issue and missing values before operational use.",
        "Raw source files were not modified.",
    ])
    report_text = "\n".join(report)
    (OUTPUT_DIR / "cleaning_report.txt").write_text(report_text, encoding="utf-8")
    print(report_text)


if __name__ == "__main__":
    main()
