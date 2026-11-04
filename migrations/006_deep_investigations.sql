CREATE TABLE IF NOT EXISTS app.deep_investigations (
 app_run_id uuid PRIMARY KEY REFERENCES app.runs, case_id uuid NOT NULL REFERENCES app.cases,
 result jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
