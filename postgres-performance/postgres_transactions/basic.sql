-- A transaction keeps the debit and credit together.
-- The CHECK constraint on balance makes an insufficient-funds debit fail.
CREATE TABLE IF NOT EXISTS bank_accounts (
    account_id INTEGER PRIMARY KEY,
    balance INTEGER NOT NULL CHECK (balance >= 0)
);

INSERT INTO bank_accounts (account_id, balance)
VALUES (1, 100), (2, 50)
ON CONFLICT (account_id) DO UPDATE SET balance = EXCLUDED.balance;

BEGIN;
UPDATE bank_accounts SET balance = balance - 10 WHERE account_id = 1;
UPDATE bank_accounts SET balance = balance + 10 WHERE account_id = 2;
COMMIT;

SELECT account_id, balance FROM bank_accounts ORDER BY account_id;
