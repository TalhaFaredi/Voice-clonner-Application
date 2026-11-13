CREATE TABLE users (
 id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL COLLATE NOCASE, name TEXT NOT NULL,
 password_hash TEXT NOT NULL, credits INTEGER NOT NULL DEFAULT 5000 CHECK(credits>=0),
 customer_id TEXT UNIQUE, created_at REAL NOT NULL
);
CREATE TABLE sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 csrf TEXT NOT NULL, expires REAL NOT NULL
);
CREATE INDEX sessions_user ON sessions(user_id);
CREATE TABLE resets (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE voices (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 name TEXT NOT NULL, ref_text TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
 consent_at REAL NOT NULL, created_at REAL NOT NULL, deleted INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX voices_user ON voices(user_id,deleted,created_at);
CREATE TABLE jobs (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, voice_id TEXT REFERENCES voices(id), text TEXT NOT NULL DEFAULT '',
 language TEXT NOT NULL DEFAULT 'auto', speaker TEXT, instruct TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL, cost INTEGER NOT NULL CHECK(cost>=0), error TEXT, duration REAL,
 idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, lease_owner TEXT, heartbeat REAL,
 created_at REAL NOT NULL, finished_at REAL, deleted INTEGER NOT NULL DEFAULT 0,
 UNIQUE(user_id,idempotency_key)
);
CREATE INDEX jobs_queue ON jobs(status,created_at);
CREATE INDEX jobs_user ON jobs(user_id,created_at);
CREATE TABLE ledger (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), amount INTEGER NOT NULL,
 reason TEXT NOT NULL, reference TEXT UNIQUE NOT NULL, created_at REAL NOT NULL
);
CREATE INDEX ledger_user ON ledger(user_id,created_at);
CREATE TABLE subscriptions (
 user_id TEXT PRIMARY KEY REFERENCES users(id), stripe_id TEXT UNIQUE, plan TEXT NOT NULL DEFAULT 'free',
 interval TEXT NOT NULL DEFAULT 'month', status TEXT NOT NULL DEFAULT 'free', period_end REAL,
 cancel_at_period_end INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE payments (
 invoice_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), amount INTEGER NOT NULL,
 currency TEXT NOT NULL, status TEXT NOT NULL, receipt_url TEXT, created_at REAL NOT NULL
);
CREATE INDEX payments_user ON payments(user_id,created_at);
CREATE TABLE webhook_events (id TEXT PRIMARY KEY, created_at REAL NOT NULL);
CREATE TABLE rate_limits (key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires REAL NOT NULL);
CREATE TABLE worker_status (id TEXT PRIMARY KEY, status TEXT NOT NULL, heartbeat REAL NOT NULL, error TEXT);
CREATE TABLE checkout_requests (user_id TEXT PRIMARY KEY REFERENCES users(id), session_id TEXT, url TEXT, expires REAL);
