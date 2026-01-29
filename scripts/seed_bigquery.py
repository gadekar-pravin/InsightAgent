#!/usr/bin/env python3
"""
Seed BigQuery with demo data for InsightAgent.

This script:
1. Creates tables in the BigQuery dataset
2. Loads seed data from CSV files
3. Verifies the data matches expected demo values

Usage:
    python scripts/seed_bigquery.py
"""

import os
import sys
from pathlib import Path

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "insightagent-adk")
DATASET_ID = os.getenv("BQ_DATASET_ID", "insightagent_data")
LOCATION = os.getenv("VERTEX_LOCATION", "asia-south1")

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "seed_data"


def get_client() -> bigquery.Client:
    """Create BigQuery client."""
    return bigquery.Client(project=PROJECT_ID, location=LOCATION)


def create_tables(client: bigquery.Client) -> None:
    """Create BigQuery tables with appropriate schemas."""
    dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"

    # Transactions table schema
    transactions_schema = [
        bigquery.SchemaField("transaction_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("region", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_line", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("customer_segment", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("quantity", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("unit_price", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("revenue", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("customer_id", "STRING", mode="REQUIRED"),
    ]

    # Customers table schema
    customers_schema = [
        bigquery.SchemaField("customer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("segment", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("region", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("acquisition_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("lifetime_value", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("churn_date", "DATE", mode="NULLABLE"),
    ]

    # Targets table schema
    targets_schema = [
        bigquery.SchemaField("target_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("region", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("year", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("quarter", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("target_amount", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("product_line", "STRING", mode="REQUIRED"),
    ]

    tables = [
        ("transactions", transactions_schema),
        ("customers", customers_schema),
        ("targets", targets_schema),
    ]

    for table_name, schema in tables:
        table_id = f"{dataset_ref}.{table_name}"

        # Delete existing table if it exists
        try:
            client.delete_table(table_id)
            print(f"  Deleted existing table: {table_name}")
        except NotFound:
            pass

        # Create new table
        table = bigquery.Table(table_id, schema=schema)
        table = client.create_table(table)
        print(f"  Created table: {table_name}")


def load_csv_to_table(client: bigquery.Client, table_name: str, csv_path: Path) -> None:
    """Load CSV file into BigQuery table."""
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # Skip header row
        autodetect=False,  # Use schema from table
    )

    with open(csv_path, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)

    job.result()  # Wait for job to complete

    # Get row count
    table = client.get_table(table_id)
    print(f"  Loaded {table.num_rows} rows into {table_name}")


def verify_data(client: bigquery.Client) -> bool:
    """Verify the loaded data matches expected demo values."""
    print("\nVerifying data...")

    all_passed = True

    # Test 1: Q4 2024 total revenue should be ~$12.4M
    query = f"""
        SELECT SUM(revenue) as total_revenue
        FROM `{PROJECT_ID}.{DATASET_ID}.transactions`
        WHERE date >= '2024-10-01' AND date <= '2024-12-31'
    """
    result = list(client.query(query).result())[0]
    q4_revenue = result.total_revenue / 1_000_000
    expected = 12.4
    passed = abs(q4_revenue - expected) < 0.5  # Allow 500K variance
    print(f"  Q4 2024 Revenue: ${q4_revenue:.2f}M (expected ~${expected}M) {'✓' if passed else '✗'}")
    all_passed = all_passed and passed

    # Test 2: Q4 2024 target should be $13.0M
    query = f"""
        SELECT SUM(target_amount) as total_target
        FROM `{PROJECT_ID}.{DATASET_ID}.targets`
        WHERE year = 2024 AND quarter = 'Q4' AND product_line = 'All'
    """
    result = list(client.query(query).result())[0]
    q4_target = result.total_target / 1_000_000
    expected = 13.0
    passed = abs(q4_target - expected) < 0.1
    print(f"  Q4 2024 Target: ${q4_target:.2f}M (expected ${expected}M) {'✓' if passed else '✗'}")
    all_passed = all_passed and passed

    # Test 3: West region Q4 2024 revenue vs target (should be ~-25.7%)
    query = f"""
        WITH west_revenue AS (
            SELECT SUM(revenue) as revenue
            FROM `{PROJECT_ID}.{DATASET_ID}.transactions`
            WHERE region = 'West'
            AND date >= '2024-10-01' AND date <= '2024-12-31'
        ),
        west_target AS (
            SELECT target_amount
            FROM `{PROJECT_ID}.{DATASET_ID}.targets`
            WHERE region = 'West' AND year = 2024 AND quarter = 'Q4' AND product_line = 'All'
        )
        SELECT
            r.revenue,
            t.target_amount,
            ((r.revenue - t.target_amount) / t.target_amount) * 100 as variance_pct
        FROM west_revenue r, west_target t
    """
    result = list(client.query(query).result())[0]
    variance = result.variance_pct
    expected = -25.7
    passed = abs(variance - expected) < 3  # Allow 3% variance
    print(f"  West Region Variance: {variance:.1f}% (expected ~{expected}%) {'✓' if passed else '✗'}")
    all_passed = all_passed and passed

    # Test 4: Q4 2023 revenue should be ~$9.6M
    query = f"""
        SELECT SUM(revenue) as total_revenue
        FROM `{PROJECT_ID}.{DATASET_ID}.transactions`
        WHERE date >= '2023-10-01' AND date <= '2023-12-31'
    """
    result = list(client.query(query).result())[0]
    q4_2023_revenue = result.total_revenue / 1_000_000
    expected = 9.6
    passed = abs(q4_2023_revenue - expected) < 0.5
    print(f"  Q4 2023 Revenue: ${q4_2023_revenue:.2f}M (expected ~${expected}M) {'✓' if passed else '✗'}")
    all_passed = all_passed and passed

    # Test 5: Churn rate check (customers with churn_date in recent period)
    query = f"""
        SELECT
            COUNT(CASE WHEN churn_date IS NOT NULL THEN 1 END) as churned,
            COUNT(*) as total
        FROM `{PROJECT_ID}.{DATASET_ID}.customers`
    """
    result = list(client.query(query).result())[0]
    churn_rate = (result.churned / result.total) * 100
    print(f"  Overall Churn: {result.churned}/{result.total} customers ({churn_rate:.1f}%)")

    return all_passed


def main():
    """Main function to seed BigQuery."""
    print(f"Seeding BigQuery dataset: {PROJECT_ID}.{DATASET_ID}")
    print(f"Location: {LOCATION}")
    print(f"Data directory: {DATA_DIR}")
    print()

    client = get_client()

    # Create tables
    print("Creating tables...")
    create_tables(client)
    print()

    # Load data
    print("Loading data from CSV files...")
    csv_files = [
        ("transactions", DATA_DIR / "transactions.csv"),
        ("customers", DATA_DIR / "customers.csv"),
        ("targets", DATA_DIR / "targets.csv"),
    ]

    for table_name, csv_path in csv_files:
        if csv_path.exists():
            load_csv_to_table(client, table_name, csv_path)
        else:
            print(f"  Warning: {csv_path} not found, skipping")

    # Verify data
    if verify_data(client):
        print("\n✓ All verification checks passed!")
    else:
        print("\n✗ Some verification checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
