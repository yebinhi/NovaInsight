CREATE TABLE IF NOT EXISTS projects (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  brand_name TEXT NOT NULL,
  website TEXT NOT NULL,
  products TEXT NOT NULL,
  country TEXT NOT NULL,
  language TEXT NOT NULL,
  audience TEXT NOT NULL,
  hoped_questions TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS competitors (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  website TEXT
);

CREATE TABLE IF NOT EXISTS questions (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  stage TEXT NOT NULL CHECK (stage IN ('discovery', 'fit', 'comparison', 'decision', 'verification')),
  branded BOOLEAN NOT NULL,
  text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_runs (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
  model TEXT NOT NULL,
  language TEXT NOT NULL,
  region TEXT NOT NULL,
  web_search BOOLEAN NOT NULL,
  channel TEXT NOT NULL CHECK (channel IN ('api', 'consumer')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS answers (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  test_run_id INTEGER NOT NULL REFERENCES test_runs (id) ON DELETE CASCADE,
  question_id INTEGER NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
  repeat_index INTEGER NOT NULL CHECK (repeat_index BETWEEN 1 AND 3),
  body TEXT NOT NULL,
  recommendation_reason TEXT NOT NULL DEFAULT '',
  cited_official BOOLEAN NOT NULL DEFAULT FALSE,
  factual_error BOOLEAN NOT NULL DEFAULT FALSE,
  error_note TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (test_run_id, question_id, repeat_index)
);

CREATE TABLE IF NOT EXISTS citations (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  answer_id INTEGER NOT NULL REFERENCES answers (id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  is_client_site BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS answer_brands (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  answer_id INTEGER NOT NULL REFERENCES answers (id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('client', 'competitor')),
  mentioned BOOLEAN NOT NULL DEFAULT FALSE,
  recommended BOOLEAN NOT NULL DEFAULT FALSE,
  negative BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (answer_id, name, role)
);

CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('site', 'external')),
  claim_type TEXT NOT NULL CHECK (claim_type IN ('fact', 'hypothesis')),
  observation TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS findings (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
  observation TEXT NOT NULL,
  action TEXT NOT NULL,
  basis TEXT NOT NULL CHECK (basis IN ('fact', 'hypothesis')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS finding_answers (
  finding_id INTEGER NOT NULL REFERENCES findings (id) ON DELETE CASCADE,
  answer_id INTEGER NOT NULL REFERENCES answers (id) ON DELETE CASCADE,
  PRIMARY KEY (finding_id, answer_id)
);
