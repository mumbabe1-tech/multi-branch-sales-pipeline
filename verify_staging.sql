-- ============================================================================
-- VERIFICATION TEST SCRIPT
-- Run these queries to prove your staging data guardrails work.
-- ============================================================================

-- TEST 1: Attempt an invalid payment method type ('Crypto')
-- EXPECTED RESULT: ERROR: new row for relation "transactions" violates check constraint "chk_txn_payment"
INSERT INTO staging.transactions (receipt_no, sale_timestamp, store_id, staff_name, product_name, quantity, payment_method, source_sheet)
VALUES ('REC-99999', NOW(), 'S001', 'Kofi Mensah', 'Rice 5kg', 2, 'Crypto', 'Saleslog_S001_Jun1-15');


-- TEST 2: Attempt an out-of-bounds quantity configuration (25 items)
-- EXPECTED RESULT: ERROR: new row for relation "transactions" violates check constraint "chk_txn_quantity"
INSERT INTO staging.transactions (receipt_no, sale_timestamp, store_id, staff_name, product_name, quantity, payment_method, source_sheet)
VALUES ('REC-99999', NOW(), 'S001', 'Kofi Mensah', 'Rice 5kg', 25, 'Cash', 'Saleslog_S001_Jun1-15');


-- TEST 3: Safe Baseline Insert (Valid configuration)
-- EXPECTED RESULT: INSERT 0 1 (Success!)
INSERT INTO staging.transactions (receipt_no, sale_timestamp, store_id, staff_name, product_name, quantity, payment_method, source_sheet)
VALUES ('REC-00001', NOW(), 'S001', 'Kofi Mensah', 'Rice 5kg', 2, 'Cash', 'Saleslog_S001_Jun1-15');