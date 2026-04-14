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
    due_date        TIMESTAMPTZ   DEFAULT NULL,
    created_at      TIMESTAMPTZ   DEFAULT NOW()
);

-- Speeds up per-user queries for /open
CREATE INDEX IF NOT EXISTS idx_inbox_user_status ON inbox (user_id, status);

-- Run this if the table already exists (adds due_date to existing installs)
ALTER TABLE inbox ADD COLUMN IF NOT EXISTS due_date TIMESTAMPTZ DEFAULT NULL;

-- Row Level Security
-- Locks down the table so only the service_role key (used by the bot) can
-- read or write. The anon/publishable key gets no access at all.
-- The bot requires no code changes — service_role bypasses RLS automatically.
ALTER TABLE inbox ENABLE ROW LEVEL SECURITY;
