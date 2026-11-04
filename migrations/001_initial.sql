CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS checkpoints;
CREATE TABLE IF NOT EXISTS app.schema_version (version int PRIMARY KEY);
CREATE TABLE IF NOT EXISTS app.customers (
  organization_id text NOT NULL, id text NOT NULL, name text NOT NULL, email text NOT NULL,
  address text NOT NULL, blocked boolean NOT NULL DEFAULT false, synthetic boolean NOT NULL DEFAULT true,
  PRIMARY KEY (organization_id,id)
);
CREATE TABLE IF NOT EXISTS app.cases (
  id uuid PRIMARY KEY, organization_id text NOT NULL, client_id text, title text NOT NULL,
  process text NOT NULL DEFAULT 'P1', status text NOT NULL DEFAULT 'open', version int NOT NULL DEFAULT 0,
  proposal jsonb, proposal_hash text, order_id uuid, order_version int, owner text NOT NULL DEFAULT 'demo_operator',
  clarification_count int NOT NULL DEFAULT 0, deadline timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app.messages (
  id uuid PRIMARY KEY, case_id uuid NOT NULL REFERENCES app.cases, role text NOT NULL,
  content text NOT NULL, metadata jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app.runs (
  id uuid PRIMARY KEY, case_id uuid NOT NULL REFERENCES app.cases, organization_id text NOT NULL,
  input jsonb NOT NULL, input_hash text NOT NULL, status text NOT NULL DEFAULT 'queued',
  cancelled boolean NOT NULL DEFAULT false, attempts int NOT NULL DEFAULT 0, lease_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz
);
CREATE UNIQUE INDEX IF NOT EXISTS one_run_per_case ON app.runs(case_id) WHERE status IN ('queued','running');
CREATE TABLE IF NOT EXISTS app.events (
  sequence bigserial PRIMARY KEY, event_id uuid NOT NULL UNIQUE, run_id uuid NOT NULL REFERENCES app.runs,
  case_id uuid NOT NULL REFERENCES app.cases, type text NOT NULL, payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS event_run ON app.events(run_id,sequence);
CREATE TABLE IF NOT EXISTS app.attachments (
  id uuid PRIMARY KEY, case_id uuid NOT NULL REFERENCES app.cases, organization_id text NOT NULL,
  filename text NOT NULL, mime text NOT NULL, size int NOT NULL, hash text NOT NULL, storage_key text NOT NULL,
  pages int, duration real, observation text NOT NULL DEFAULT '', observation_version int NOT NULL DEFAULT 0,
  perception_status text NOT NULL DEFAULT 'pending', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app.orders (
  id uuid PRIMARY KEY, organization_id text NOT NULL, client_id text NOT NULL,
  request_id uuid NOT NULL UNIQUE, number text NOT NULL UNIQUE, fields jsonb NOT NULL,
  status text NOT NULL DEFAULT 'registered', version int NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(), FOREIGN KEY(organization_id,client_id) REFERENCES app.customers
);
CREATE TABLE IF NOT EXISTS app.slots (
  id text PRIMARY KEY, organization_id text NOT NULL, day date NOT NULL, shift text NOT NULL,
  capacity int NOT NULL CHECK(capacity>=0), reserved int NOT NULL DEFAULT 0 CHECK(reserved>=0 AND reserved<=capacity),
  version int NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS app.reservations (
  order_id uuid NOT NULL REFERENCES app.orders, operation text NOT NULL, slot_id text NOT NULL REFERENCES app.slots,
  PRIMARY KEY(order_id,operation)
);
CREATE TABLE IF NOT EXISTS app.approvals (
  id uuid PRIMARY KEY, case_id uuid NOT NULL REFERENCES app.cases, organization_id text NOT NULL,
  proposal_hash text NOT NULL, case_version int NOT NULL, order_version int, policy_version text NOT NULL,
  required_role text NOT NULL, kind text NOT NULL, status text NOT NULL DEFAULT 'pending',
  actor_id text, decision_id uuid UNIQUE, decision jsonb, decided_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app.operator_events (
  id uuid PRIMARY KEY, case_id uuid NOT NULL REFERENCES app.cases, organization_id text NOT NULL,
  actor_id text NOT NULL, kind text NOT NULL, note text NOT NULL, attachment_id uuid REFERENCES app.attachments,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app.command_ledger (
  organization_id text NOT NULL, command_id uuid NOT NULL, case_id uuid NOT NULL REFERENCES app.cases,
  payload_hash text NOT NULL, result jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(organization_id,command_id)
);
CREATE TABLE IF NOT EXISTS app.outbox (
  id uuid PRIMARY KEY, case_id uuid NOT NULL REFERENCES app.cases, payload jsonb NOT NULL,
  channel text NOT NULL DEFAULT 'local_inbox', status text NOT NULL DEFAULT 'pending', attempts int NOT NULL DEFAULT 0,
  next_attempt_at timestamptz NOT NULL DEFAULT now(), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app.inbox (
  event_id uuid PRIMARY KEY REFERENCES app.outbox, case_id uuid NOT NULL REFERENCES app.cases,
  payload jsonb NOT NULL, delivered_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app.collections (
  id text PRIMARY KEY, model text NOT NULL, dimension int NOT NULL, verified_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS app.documents (
  id text PRIMARY KEY, organization_id text NOT NULL, client_id text, roles text[] NOT NULL,
  title text NOT NULL, version text NOT NULL, hash text NOT NULL, approved boolean NOT NULL,
  valid_from timestamptz NOT NULL, valid_until timestamptz, synthetic boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS app.chunks (
  id text PRIMARY KEY, document_id text NOT NULL REFERENCES app.documents,
  collection_id text NOT NULL REFERENCES app.collections, section text NOT NULL, page int,
  content text NOT NULL, hash text NOT NULL, embedding vector NOT NULL
);
INSERT INTO app.schema_version VALUES (1) ON CONFLICT DO NOTHING;
