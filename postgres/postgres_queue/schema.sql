CREATE TABLE IF NOT EXISTS queue_jobs (
    job_id UUID PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    job_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'processing', 'retrying', 'completed', 'dead_lettered')
    ),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_until TIMESTAMPTZ,
    claim_token UUID,
    result JSONB,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS queue_jobs_ready_idx
    ON queue_jobs (available_at, created_at)
    WHERE status IN ('queued', 'retrying');

CREATE INDEX IF NOT EXISTS queue_jobs_expired_lease_idx
    ON queue_jobs (locked_until)
    WHERE status = 'processing';

CREATE INDEX IF NOT EXISTS queue_jobs_dead_letter_idx
    ON queue_jobs (updated_at DESC)
    WHERE status = 'dead_lettered';
