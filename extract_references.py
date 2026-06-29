# Extraction and loading script from Google Sheets to PostgreSQL
# Dynamically creates raw.transactions based on Google Sheet headers.

import os
import logging
import re
import gspread
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

STORE_SHEETS = {
    "Saleslog_S001_Jun1-15": "1dob3p4TRkWj-jN3imsNcihFSajZ_9u4ZkEKWdBVrDV8",
    "Saleslog_S002_Jun1-15": "1hEb2KZZlqD_cyRfSF8KDiPCAcQ8Igqr89ooJ2yfqstg",
    "Saleslog_S003_Jun1-15": "1NkNRsHkMO8jg5BCG0igHYdorFqKx-APmoRR5K15muDo",
    "Saleslog_S004_Jun1-15": "1iAgxk_XP8rZBXxHa6zH7YZQno3vVqaEVD8vpHuqB-2U",
    "Saleslog_S005_Jun1-15": "1R04N8FmX3KeMdKb9-cSZDgluBq2N4Q8_WNAsXOXbGlc",
    "Saleslog_S006_Jun1-15": "1q5_-lY_trscnJOwiFWedyOOPC2agq0vnqnXVTc9IgG0",
    "Saleslog_S007_Jun1-15": "1imTaeiPNKWO2jLg5YBjny6UlcXnlFqkHcNKvj0cDBJ4",
    "Saleslog_S008_Jun1-15": "1OXcsRtjx7GSbtVmvDZr-KogCVXsEhe_AkUoF9wOyngw",
    "Saleslog_S009_Jun1-15": "1sXTnfqBRcg1u_-DRyn_-yWZdIGG96E_mQoHsiHJz6FA",
    "Saleslog_S010_Jun1-15": "1CHfGZ6-D_meZj3t5y3KIWu3qvD9vNTWdS24udz23zmE",
    "Saleslog_S011_Jun1-15": "10u8ny3KHNSQ1SCSCwEjdmFiULhPcrn5wSnK-RVB6REM",
}

LOG_FILE = "extract.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

def clean_row(row_dict):
    return tuple(value if value != "" else None for value in row_dict.values())

def sanitize_header(header_str):
    s = header_str.strip().lower().replace(" ", "_")
    s = re.sub(r'[^a-z0-9_]', '', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s

def main():
    logging.info("Starting extraction workflow...")

    gc = gspread.oauth()
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Create schema if missing
    cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    conn.commit()

    all_store_data = {}
    discovered_columns = set()

    # Step 1: Read all sheets first to collect data and discover columns dynamically
    for sheet_name, sheet_id in STORE_SHEETS.items():
        logging.info(f"Reading headers and rows from: {sheet_name}")
        try:
            spreadsheet = gc.open_by_key(sheet_id)
            worksheet = spreadsheet.get_worksheet(0)
            records = worksheet.get_all_records()
            
            if records:
                all_store_data[sheet_name] = records
                # Track every unique column name across all sheets
                for col in records[0].keys():
                    discovered_columns.add(sanitize_header(col))
        except Exception as e:
            logging.error(f"Could not read sheet {sheet_name}. Error: {e}")
            continue

    if not all_store_data:
        logging.error("No data found in any sheets. Exiting.")
        return

    # Add our pipeline-tracking source column
    discovered_columns.add("source_sheet")
    column_list_sorted = sorted(list(discovered_columns))

    # Step 2: Dynamically build the table using the discovered columns
    logging.info("Re-creating raw.transactions with a dynamic schema...")
    cur.execute("DROP TABLE IF EXISTS raw.transactions CASCADE;")
    
    # All columns will safely accept TEXT/VARCHAR to prevent ingestion crashes
    table_columns_sql = ", ".join([f'"{col}" VARCHAR' for col in column_list_sorted])
    create_table_sql = f"CREATE TABLE raw.transactions ({table_columns_sql});"
    cur.execute(create_table_sql)
    conn.commit()

    total_rows = 0

    # Step 3: Insert rows by mapping them to our new dynamic layout
    for sheet_name, records in all_store_data.items():
        logging.info(f"Loading data from {sheet_name} into database...")
        
        for r in records:
            # Build a dictionary where keys are sanitized
            sanitized_record = {sanitize_header(k): (v if v != "" else None) for k, v in r.items()}
            sanitized_record["source_sheet"] = sheet_name
            
            # Align sheet values with our master table column ordering
            row_tuple = tuple(sanitized_record.get(col) for col in column_list_sorted)
            
            safe_columns = [f'"{col}"' for col in column_list_sorted]
            column_list_str = ", ".join(safe_columns)
            placeholders = ", ".join(["%s"] * len(column_list_sorted))
            insert_sql = f"INSERT INTO raw.transactions ({column_list_str}) VALUES ({placeholders})"
            
            cur.execute(insert_sql, row_tuple)

        conn.commit()
        logging.info(f"{sheet_name}: {len(records)} rows loaded.")
        total_rows += len(records)

    cur.close()
    conn.close()
    logging.info(f"Extraction completed successfully! Total rows loaded: {total_rows}")

if __name__ == "__main__":
    main()