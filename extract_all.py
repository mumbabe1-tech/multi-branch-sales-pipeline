"""
extract_all.py
-----------------------------------------
Unified extraction script for all 15 Google Sheets:
- 11 store transaction sheets
- 4 reference master sheets

1. Connect to Google Sheets and Postgres
2. Pull all raw rows from each sheet
3. Normalise column names where needed
4. Load everything into the raw schema
5.
"""

import os
import logging
import re
import time  # Standard library tracking tool to safely bypass Google API 429 quotas
import gspread
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Basic database connection settings
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

# Store sheet IDs (already provided)
STORE_CONFIG = {
    "S001": "1dob3p4TRkWj-jN3imsNcihFSajZ_9u4ZkEKWdBVrDV8",
    "S002": "1hEb2KZZlqD_cyRfSF8KDiPCAcQ8Igqr89ooJ2yfqstg",
    "S003": "1NkNRsHkMO8jg5BCG0igHYdorFqKx-APmoRR5K15muDo",
    "S004": "1iAgxk_XP8rZBXxHa6zH7YZQno3vVqaEVD8vpHuqB-2U",
    "S005": "1R04N8FmX3KeMdKb9-cSZDgluBq2N4Q8_WNAsXOXbGlc",
    "S006": "1q5_-lY_trscnJOwiFWedyOOPC2agq0vnqnXVTc9IgG0",
    "S007": "1imTaeiPNKWO2jLg5YBjny6UlcXnlFqkHcNKvj0cDBJ4",
    "S008": "1OXcsRtjx7GSbtVmvDZr-KogCVXsEhe_AkUoF9wOyngw",
    "S009": "1sXTnfqBRcg1u_-DRyn_-yWZdIGG96E_mQoHsiHJz6FA",
    "S010": "1CHfGZ6-D_meZj3t5y3KIWu3qvD9vNTWdS24udz23zmE",
    "S011": "10u8ny3KHNSQ1SCSCwEjdmFiULhPcrn5wSnK-RVB6REM",
}

# Reference sheet IDs (to be replaced with real ones)
REFERENCE_SHEETS = {
    "products": "1oDXxaZLD2KP1U4bfxtY9YiipIaA2FABDL19adSCw2rk",
    "staff": "1iR3ghJkSiEV11ZrVtcvCKbwRhke9HeictvA6f-sVEZ0",
    "managers": "1shTuXYx7jrUOi6aXWDHfFwTI_1sQCGuIAngOk_UxpkM",
    "stores": "1VLadzdv5sba3iFEg8Un2OkE_tlnFeNaHg2YxWvH8Az8"
}

# Canonical column names for raw.transactions
CANONICAL_COLUMNS = [
    "receipt_no", "sale_timestamp", "store_id", "staff_name",
    "product_name", "quantity", "payment_method",
    "customer_phone", "source_sheet"
]

# Logging setup so I can see what the script is doing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("extract.log"), logging.StreamHandler()]
)

# Clean and map headers from different store forms
def normalise_header(header):
    """
    Some stores use slightly different column names.
    This function maps them to a standard set.
    """
    h = header.strip().lower().replace(" ", "_")
    h = re.sub(r'[^a-z0-9_]', '', h)

    mapping = {
        "receipt_number": "receipt_no",
        "timestamp": "sale_timestamp",
        "cashier_name": "staff_name",
        "staff_member": "staff_name",
        "product_sold": "product_name",
        "item": "product_name",
        "qty": "quantity",
        "phone": "customer_phone",
        "customer_number": "customer_phone"
    }

    return mapping.get(h, h)

def main():
    logging.info("Starting unified extraction for all 15 sheets...")

    # Connect to Google Sheets and PostgreSQL
    try:
        gc = gspread.oauth()
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
    except Exception as e:
        logging.error(f"Connection failed: {e}")
        return

    # ---------------------------------------------------------
    # PHASE 1: Build raw.transactions table fresh
    # ---------------------------------------------------------
    logging.info("Preparing raw.transactions table...")

    cur.execute("DROP TABLE IF EXISTS raw.transactions CASCADE;")
    columns_sql = ", ".join([f'"{col}" TEXT' for col in CANONICAL_COLUMNS])
    cur.execute(
        f"""
        CREATE TABLE raw.transactions (
            {columns_sql},
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()

    # ---------------------------------------------------------
    # PHASE 2: Load all 11 store sheets into raw.transactions
    # ---------------------------------------------------------
    for store_id, sheet_id in STORE_CONFIG.items():
        logging.info(f"Extracting store sheet: {store_id}")

        try:
            # Sleep 2 seconds to systematically prevent Read Quota Exceeded (429) spikes
            time.sleep(2)

            worksheet = gc.open_by_key(sheet_id).get_worksheet(0)
            records = worksheet.get_all_records()

            if not records:
                logging.warning(f"No rows found for {store_id}. Skipping.")
                continue

            for row in records:
                # Normalise column names
                cleaned = {normalise_header(k): v for k, v in row.items()}

                # Add store metadata
                cleaned["store_id"] = store_id
                cleaned["source_sheet"] = f"Saleslog_{store_id}_Jun1-15"

                # Build row in correct column order
                row_values = []
                for col in CANONICAL_COLUMNS:
                    val = cleaned.get(col, None)
                    row_values.append(str(val) if val not in ("", None) else None)

                placeholders = ", ".join(["%s"] * len(CANONICAL_COLUMNS))
                insert_sql = (
                    f"INSERT INTO raw.transactions "
                    f"({', '.join([f'\"{c}\"' for c in CANONICAL_COLUMNS])}) "
                    f"VALUES ({placeholders})"
                )

                cur.execute(insert_sql, tuple(row_values))

            conn.commit()
            logging.info(f"{store_id}: {len(records)} rows loaded.")

        except Exception as e:
            conn.rollback()
            logging.error(f"Failed to load store {store_id}: {e}")

    # ---------------------------------------------------------
    # PHASE 3: Refresh the 4 reference tables
    # ---------------------------------------------------------
    logging.info("Refreshing reference tables...")

    # Resolved NameError: Using REFERENCE_SHEETS config dictionary cleanly
    for table_name, sheet_id in REFERENCE_SHEETS.items():
        logging.info(f"Loading reference table: raw.{table_name}")

        try:
            # Sleep 2 seconds to space out calls safely for reference catalog extractions
            time.sleep(2)

            worksheet = gc.open_by_key(sheet_id).get_worksheet(0)
            records = worksheet.get_all_records()

            if not records:
                logging.warning(f"No data found for raw.{table_name}. Skipping.")
                continue

            # Clear table before loading new data
            cur.execute(f'TRUNCATE TABLE raw.{table_name} CASCADE;')

            # Clean headers
            headers = [
                re.sub(r'[^a-z0-9_]', '', k.strip().lower().replace(" ", "_"))
                for k in records[0].keys()
            ]

            insert_sql = (
                f"INSERT INTO raw.{table_name} "
                f"({', '.join([f'\"{h}\"' for h in headers])}) "
                f"VALUES ({', '.join(['%s'] * len(headers))})"
            )

            for row in records:
                cleaned_row = tuple(str(v) if v != "" else None for v in row.values())
                cur.execute(insert_sql, cleaned_row)

            conn.commit()
            logging.info(f"raw.{table_name}: {len(records)} rows loaded.")

        except Exception as e:
            conn.rollback()
            logging.error(f"Failed loading raw.{table_name}: {e}")

    # Close connections
    cur.close()
    conn.close()
    logging.info("Unified extraction completed successfully.")

if __name__ == "__main__":
    main()