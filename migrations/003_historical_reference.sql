CREATE SCHEMA IF NOT EXISTS reference;
CREATE TABLE IF NOT EXISTS reference.imports (
 id text PRIMARY KEY, publisher text NOT NULL, api_url text NOT NULL, retrieved_at timestamptz NOT NULL,
 cutoff_date date NOT NULL, sha256 text NOT NULL, record_count int NOT NULL, selection jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS reference.recalls (
 id text PRIMARY KEY, import_id text NOT NULL REFERENCES reference.imports,
 recall_number text NOT NULL UNIQUE, event_date date NOT NULL, title text NOT NULL,
 source_url text NOT NULL, products jsonb NOT NULL, hazards jsonb NOT NULL, remedies jsonb NOT NULL,
 source_hash text NOT NULL, source_payload jsonb NOT NULL, synthetic boolean NOT NULL DEFAULT false CHECK(synthetic=false)
);
ALTER TABLE app.cases ADD COLUMN IF NOT EXISTS synthetic boolean NOT NULL DEFAULT true;
ALTER TABLE app.cases ADD COLUMN IF NOT EXISTS data_origin text NOT NULL DEFAULT 'demo_local';
ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS synthetic boolean NOT NULL DEFAULT true;
