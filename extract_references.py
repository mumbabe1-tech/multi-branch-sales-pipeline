"""
 Reference Sheets Extraction Script
----------------------------------
This script pulls data from the four master Google Sheets
(Products, Staff, Managers, Stores) and loads them into the
matching raw tables in PostgreSQL.

- connect to Google Sheets
- read all rows
- clean the column names a bit
- truncate the raw table
- insert everything fresh
"""

import os
import logging
import re
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

# Google Sheet IDs for each reference table
# (I still need to replace these with the real IDs)
REFERENCE_SHEETS = {
    "products": "1oDXxaZLD2KP1U4bfxtY9YiipIaA2FABDL19adSCw2rk",
    "staff": "1iR3ghJkSiEV11ZrVtcvCKbwRhke9HeictvA6f-sVEZ0",
    "managers": "1shTuXYx7jrUOi6aXWDHfFwTI_1sQCGuIAngOk_UxpkM",
    "stores": "1VLadzdv5sba3iFEg8Un2OkE_tlnFeNaHg2YxWvH8Az8"
}

# Logging setup so I can see what the script is doing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("extract.log"),
        logging.StreamHandler()
    ]
)

# Clean column names so they work well in SQL
def sanitize_header(header):
    header = header.strip().lower().replace(" ", "_")
    header = re.sub(r'[^a-z0-9_]', '', header)
    header = re.sub(r'_+', '_', header)
    return header.strip('_')

def main():
    logging.info("Starting reference sheets extraction...")

    # Connect to Google Sheets and PostgreSQL
    try:
        gc = gspread.oauth()
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
    except Exception as e:
        logging.error(f"Could not connect to Google Sheets or Postgres: {e}")
        return

    # Loop through each reference sheet and load it into raw.<table>
    for table_name, sheet_id in REFERENCE_SHEETS.items():
        logging.info(f"Working on raw.{table_name}...")

        try:
            # Read sheet as list of dictionaries
            worksheet = gc.open_by_key(sheet_id).get_worksheet(0)
            records = worksheet.get_all_records()

            if not records:
                logging.warning(f"No data found for raw.{table_name}. Skipping.")
                continue

            # Clear the table before loading new data
            cur.execute(f'TRUNCATE TABLE raw.{table_name} CASCADE;')

            # Prepare SQL insert statement
            headers = [sanitize_header(col) for col in records[0].keys()]
            column_list = ", ".join([f'"{h}"' for h in headers])
            placeholders = ", ".join(["%s"] * len(headers))
            insert_sql = f"INSERT INTO raw.{table_name} ({column_list}) VALUES ({placeholders})"

            # Insert each row
            for row in records:
                cleaned_row = tuple(str(v) if v != "" else None for v in row.values())
                cur.execute(insert_sql, cleaned_row)

            conn.commit()
            logging.info(f"raw.{table_name}: {len(records)} rows loaded successfully.")

        except Exception as e:
            conn.rollback()
            logging.error(f"Failed to load raw.{table_name}: {e}")

    # Close connections
    cur.close()
    conn.close()
    logging.info("Reference sheets extraction completed.")

if __name__ == "__main__":
    main()
