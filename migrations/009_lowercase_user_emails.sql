-- Store emails lowercase so "Nate@x.com" and "nate@x.com" are one account. The routes now lowercase
-- on read; this fixes existing rows, and the NOCASE index blocks case-duplicates if a path forgets.
BEGIN TRANSACTION;

UPDATE users SET email = lower(email) WHERE email != lower(email);

CREATE UNIQUE INDEX idx_users_email_nocase
ON users(email COLLATE NOCASE);

COMMIT;
