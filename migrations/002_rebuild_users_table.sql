-- Rebuild users table 
-- Rename password, date_created, verification_token, and reset_token to 
-- Password_hash, created_at, verification_token_created_at, and reset_token_created_at respectively
-- Also changing data types for created_at, verification_token_created_at, and reset_token_created_at to TEXT
-- Add datetime CHECK constraints for created_at, verification_token_created_at, and reset_token_created_at

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

CREATE TABLE users_new (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    verified INTEGER DEFAULT 0,
    verification_token TEXT,
    verification_token_created_at TEXT,
    reset_token TEXT,
    reset_token_created_at TEXT,
    CHECK(datetime(created_at) IS NOT NULL),
    CHECK(verification_token_created_at IS NULL OR datetime(verification_token_created_at) IS NOT NULL),
    CHECK(reset_token_created_at IS NULL OR datetime(reset_token_created_at) IS NOT NULL)
);

INSERT INTO users_new (id, first_name, last_name, username, email, password_hash, 
                       created_at, verified, verification_token, verification_token_created_at,
                       reset_token, reset_token_created_at)
SELECT id, first_name, last_name, username, email, password, 
                       date_created, verified, verification_token, token_created_at,
                       reset_token, reset_token_created_at FROM users;

DROP TABLE users;
ALTER TABLE users_new RENAME TO users;

COMMIT;

PRAGMA foreign_keys = ON;
