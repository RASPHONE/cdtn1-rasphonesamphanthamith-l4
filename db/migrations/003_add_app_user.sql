-- 003 — demo login accounts in the database, passwords stored only as hashes.
-- BT3 security checklist item 4 / SE S3, BUG-014: until v0.2 the two demo accounts and
-- their passwords were a dictionary in src/services/auth_service.py, compared in plain text.
-- Rows are loaded by scripts/seed.py (hash computed at seed time, never stored in clear).

CREATE TABLE IF NOT EXISTS app_user (                            -- FR12, QT-14
    user_id        BIGINT       PRIMARY KEY,
    username       VARCHAR(50)  NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    role           VARCHAR(30)  NOT NULL,
    center_id      BIGINT       NOT NULL,                        -- QT-14: written into the token
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_app_user_role CHECK (role IN ('CENTER_MANAGER', 'TECHNICIAN')),
    -- Refuses anything that is not a PBKDF2 hash string, e.g. a password in clear.
    CONSTRAINT chk_app_user_password_hash CHECK (password_hash LIKE 'pbkdf2_sha256$%')
);
