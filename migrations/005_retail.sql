-- Additive: existing orders are explicitly legacy, with no fabricated items/payments.
ALTER TABLE app.customers ALTER COLUMN email DROP NOT NULL;
ALTER TABLE app.customers ALTER COLUMN address SET DEFAULT '';
ALTER TABLE app.customers ADD COLUMN IF NOT EXISTS contact text;
ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'legacy_v1';
ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS received_at timestamptz;
ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS promised_at timestamptz;
ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS currency text;
ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS total numeric(12,2);
ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS quote jsonb;
ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS processing_started_at timestamptz;
ALTER TABLE app.cases ADD COLUMN IF NOT EXISTS parent_case_id uuid REFERENCES app.cases;
CREATE TABLE app.pickup_requests (
 id uuid PRIMARY KEY, organization_id text NOT NULL, client_id text NOT NULL,
 request_id uuid NOT NULL UNIQUE REFERENCES app.cases, fields jsonb NOT NULL,
 status text NOT NULL DEFAULT 'REQUESTED', version int NOT NULL DEFAULT 1,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(organization_id,client_id) REFERENCES app.customers
);
ALTER TABLE app.cases ADD COLUMN IF NOT EXISTS pickup_request_id uuid REFERENCES app.pickup_requests;
ALTER TABLE app.cases ADD COLUMN IF NOT EXISTS pickup_version int;
ALTER TABLE app.approvals ADD COLUMN IF NOT EXISTS pickup_version int;
ALTER TABLE app.orders ADD COLUMN IF NOT EXISTS pickup_request_id uuid UNIQUE REFERENCES app.pickup_requests;
CREATE TABLE app.order_items (
 id uuid PRIMARY KEY, order_id uuid NOT NULL REFERENCES app.orders, position int NOT NULL,
 garment text NOT NULL, quantity int NOT NULL CHECK(quantity>0), weight_kg numeric(10,3),
 service_code text NOT NULL, observations text NOT NULL, evidence_refs jsonb NOT NULL,
 unit_price numeric(12,2) NOT NULL, amount numeric(12,2) NOT NULL,
 UNIQUE(order_id,position)
);
CREATE TABLE app.payment_records (
 id uuid PRIMARY KEY, order_id uuid NOT NULL REFERENCES app.orders, amount numeric(12,2) NOT NULL CHECK(amount>0),
 concept text NOT NULL, evidence text NOT NULL, actor_id text NOT NULL, declared_at timestamptz NOT NULL
);
CREATE TABLE app.demo_receipts (
 id uuid PRIMARY KEY, order_id uuid NOT NULL REFERENCES app.orders, kind text NOT NULL,
 payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(order_id,kind)
);
CREATE TABLE app.retail_events (
 id uuid PRIMARY KEY, order_id uuid REFERENCES app.orders, pickup_request_id uuid REFERENCES app.pickup_requests,
 case_id uuid NOT NULL REFERENCES app.cases, kind text NOT NULL, payload jsonb NOT NULL,
 actor_id text NOT NULL, created_at timestamptz NOT NULL, CHECK(num_nonnulls(order_id,pickup_request_id)=1)
);
CREATE TABLE app.delivery_evidence (
 id uuid PRIMARY KEY, order_id uuid NOT NULL UNIQUE REFERENCES app.orders,
 receiver text NOT NULL, evidence text NOT NULL, conformity boolean NOT NULL,
 delivered_at timestamptz NOT NULL, actor_id text NOT NULL
);
CREATE TABLE app.retail_reservations (
 target_id uuid NOT NULL, operation text NOT NULL CHECK(operation IN ('pickup','delivery')),
 slot_id text NOT NULL REFERENCES app.slots, PRIMARY KEY(target_id,operation)
);
CREATE TABLE app.processing_alerts (
 order_id uuid PRIMARY KEY REFERENCES app.orders, outbox_id uuid NOT NULL UNIQUE REFERENCES app.outbox,
 threshold_hours int NOT NULL, created_at timestamptz NOT NULL
);
CREATE TABLE app.trace_links (
 app_run_id uuid NOT NULL REFERENCES app.runs, span_id uuid NOT NULL,
 trace_id uuid NOT NULL, thread_id text NOT NULL, url text, PRIMARY KEY(app_run_id,span_id)
);
