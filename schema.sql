-- Run this once in your Supabase SQL editor to create the inbox table.

CREATE TABLE IF NOT EXISTS inbox (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT        NOT NULL,
    timestamp       TIMESTAMPTZ   NOT NULL,
    originally_from TEXT,
    original_chat   TEXT,
    message         TEXT,
    has_media       BOOLEAN       DEFAULT FALSE,
    status          TEXT          DEFAULT 'Open',
    notes           TEXT          DEFAULT '',
    created_at      TIMESTAMPTZ   DEFAULT NOW()
);

-- Speeds up per-user queries for /open
CREATE INDEX IF NOT EXISTS idx_inbox_user_status ON inbox (user_id, status);
