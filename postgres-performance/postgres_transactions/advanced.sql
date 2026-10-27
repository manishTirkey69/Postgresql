-- Session A: lock the source row, then leave this transaction open.
BEGIN;
SELECT account_id, balance
FROM bank_accounts
WHERE account_id = 1
FOR UPDATE;

-- While this script pauses, run an UPDATE on account 1 in Session B and
-- observe it wait. The transaction continues and releases the lock after 10s.
SELECT 'Row lock held; issue the competing UPDATE in Session B now.' AS instruction;
SELECT pg_sleep(10);
UPDATE bank_accounts
SET balance = balance - 20
WHERE account_id = 1 AND balance >= 20;
COMMIT;
