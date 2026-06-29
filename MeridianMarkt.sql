SELECT COUNT(*), source_sheet FROM raw.transactions GROUP BY source_sheet;

-- Create the raw staging schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS raw;

-- 1. Transactions Table (Consolidated layout from all 11 store sheets)
CREATE TABLE IF NOT EXISTS raw.transactions (
    "timestamp" TEXT,
    "store_id" TEXT,
    "staff_name" TEXT,
    "staff_id" TEXT,
    "receipt_no" TEXT,
    "customer_phone_number_optional" TEXT,
    "reference_id" TEXT,
    "product_name" TEXT,
    "product_sold" TEXT, -- Accounts for sheet variations dynamically
    "category" TEXT,
    "quantity_sold" TEXT,
    "unit_price" TEXT,
    "total_price" TEXT,
    "payment_method" TEXT,
    "source_sheet" TEXT,
    "extracted_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Products Reference Table
CREATE TABLE IF NOT EXISTS raw.products (
    "product_id" TEXT,
    "product_name" TEXT,
    "category" TEXT,
    "cost_price" TEXT,
    "sale_price" TEXT,
    "extracted_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Staff Reference Table
CREATE TABLE IF NOT EXISTS raw.staff (
    "staff_id" TEXT,
    "staff_name" TEXT,
    "store_id" TEXT,
    "role" TEXT,
    "extracted_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Managers Reference Table
CREATE TABLE IF NOT EXISTS raw.managers (
    "manager_id" TEXT,
    "manager_name" TEXT,
    "region" TEXT,
    "extracted_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Stores Reference Table
CREATE TABLE IF NOT EXISTS raw.stores (
    "store_id" TEXT,
    "store_name" TEXT,
    "location" TEXT,
    "manager_id" TEXT,
    "extracted_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

SELECT source_sheet, COUNT(*) 
FROM raw.transactions 
GROUP BY source_sheet
ORDER BY source_sheet;