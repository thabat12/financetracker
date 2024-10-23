
-- This is the type of statement that will be executed in data_util.py for
--  `db_batch_update_merchants_data`.
PREPARE insert_merchants_test AS
    INSERT INTO merchant (merchant_id, merchant_name, merchant_logo) 
    VALUES ('eyg8o776k0QmNgVpAmaQj4WgzW9Qzo6O51gdd', $1, $2), 
            ('NKDjqyAdQQzpyeD8qpLnX0D6yvLe2KYKYYzQ4', $3, $4), 
            ('vzWXDWBjB06j5BJoD3Jo84OJZg7JJzmqOZA22', $5, $6), 
            ('NZAJQ5wYdo1W1p39X5q5gpb15OMe39pj4pJBb', $7, $8), 
            ('3LmdknrdwVy9vm0dqj417rLKeJXW7veV7eb2e', $9, $10) 
    ON CONFLICT (merchant_id) 
        DO UPDATE SET merchant_name = EXCLUDED.merchant_name, merchant_logo = EXCLUDED.merchant_logo;

EXECUTE insert_merchants_test(
    'Uber', 'https://plaid-merchant-logos.plaid.com/uber_1060.png', 
    'United Airlines', 'https://plaid-merchant-logos.plaid.com/united_airlines_1065.png', 
    'McDonald''s', 'https://plaid-merchant-logos.plaid.com/mcdonalds_619.png', 
    'Starbucks', 'https://plaid-merchant-logos.plaid.com/starbucks_956.png', 
    'KFC', 'https://plaid-merchant-logos.plaid.com/kfc_546.png');

DEALLOCATE insert_merchants_test;