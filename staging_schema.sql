-- ============================================================================
-- FILE: staging_schema.sql
-- DESCRIPTION: DDL for the Staging Layer & Audit Tracking Framework
--              Promotes raw TEXT data to validated, typed columns with 
--              strict structural and CHECK constraints.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS audit;

-- ----------------------------------------------------------------------------
-- TABLE: staging.stores
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.stores CASCADE;
CREATE TABLE staging.stores (
    store_id   VARCHAR(10) PRIMARY KEY,
    city       VARCHAR(50) NOT NULL,
    region     VARCHAR(30) NOT NULL,
    CONSTRAINT chk_store_region CHECK (region IN ('Southern', 'Middle Belt', 'Northern'))
);

-- ----------------------------------------------------------------------------
-- TABLE: staging.managers
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.managers CASCADE;
CREATE TABLE staging.managers (
    manager_id     VARCHAR(15) PRIMARY KEY,
    full_name      VARCHAR(100) NOT NULL,
    role           VARCHAR(50) NOT NULL,
    store_id       VARCHAR(50) NOT NULL, -- References branch name or region
    phone_number   VARCHAR(20) NOT NULL,
    email          VARCHAR(100) NOT NULL,
    date_appointed DATE NOT NULL,
    reports_to     VARCHAR(15),          -- Self-referencing field
    CONSTRAINT chk_manager_role CHECK (role IN ('Store Manager', 'Assistant Store Manager', 'Regional Manager'))
);

-- ----------------------------------------------------------------------------
-- TABLE: staging.products
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.products CASCADE;
CREATE TABLE staging.products (
    product_id     VARCHAR(15) PRIMARY KEY,
    product_name   VARCHAR(100) NOT NULL,
    category       VARCHAR(50) NOT NULL,
    unit_price_ghs DECIMAL(10, 2) NOT NULL,
    last_updated   DATE NOT NULL,
    updated_by     VARCHAR(15) NOT NULL, -- FK logic to managers handled at Marts stage
    CONSTRAINT chk_product_price CHECK (unit_price_ghs >= 0.00)
);

-- ----------------------------------------------------------------------------
-- TABLE: staging.staff
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.staff CASCADE;
CREATE TABLE staging.staff (
    staff_id          VARCHAR(15) PRIMARY KEY,
    full_name         VARCHAR(100) NOT NULL,
    role              VARCHAR(50) NOT NULL,
    store_id          VARCHAR(10) NOT NULL,
    phone_number      VARCHAR(20) NOT NULL,
    date_hired        DATE NOT NULL,
    employment_status VARCHAR(20) NOT NULL,
    CONSTRAINT chk_staff_status CHECK (employment_status IN ('Active', 'Inactive')),
    CONSTRAINT chk_staff_role CHECK (role IN ('Cashier', 'Stock Clerk', 'Sales Associate', 'Security'))
);

-- ----------------------------------------------------------------------------
-- TABLE: staging.transactions
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.transactions CASCADE;
CREATE TABLE staging.transactions (
    receipt_no     VARCHAR(50) NOT NULL,
    sale_timestamp TIMESTAMP NOT NULL,
    store_id       VARCHAR(10) NOT NULL,
    staff_name     VARCHAR(100) NOT NULL,
    product_name   VARCHAR(100) NOT NULL,
    quantity       INTEGER NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    customer_phone VARCHAR(20),
    source_sheet   VARCHAR(100) NOT NULL,
    staged_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Activity Requirements: Range and Categorical Boundary Checks
    CONSTRAINT chk_txn_quantity CHECK (quantity BETWEEN 1 AND 20),
    CONSTRAINT chk_txn_payment  CHECK (payment_method IN ('Cash', 'Card', 'Transfer'))
);

-- ----------------------------------------------------------------------------
-- TABLE: audit.validation_log
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS audit.validation_log CASCADE;
CREATE TABLE audit.validation_log (
    log_id      SERIAL PRIMARY KEY,
    check_name  VARCHAR(100) NOT NULL,  -- e.g., 'Negative Price', 'Orphaned Store ID'
    store_id    VARCHAR(10),
    raw_value   TEXT,
    flagged_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP    
);