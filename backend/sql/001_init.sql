CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS owners (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  owner_id TEXT NOT NULL REFERENCES owners(id),
  venue_type TEXT NOT NULL,
  project_year INTEGER NOT NULL,
  location TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS suppliers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  contact_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS themes (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (name, category)
);

CREATE TABLE IF NOT EXISTS materials (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS interactions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS exhibits (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  theme_id TEXT NOT NULL REFERENCES themes(id),
  project_id TEXT NOT NULL REFERENCES projects(id),
  supplier_id TEXT NOT NULL REFERENCES suppliers(id),
  budget_min INTEGER NOT NULL CHECK (budget_min >= 0),
  budget_max INTEGER NOT NULL CHECK (budget_max >= budget_min),
  dimensions TEXT NOT NULL,
  status TEXT NOT NULL,
  description TEXT NOT NULL,
  tags TEXT[] NOT NULL DEFAULT '{}',
  embedding vector(1536),
  deleted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS exhibit_materials (
  exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
  material_id TEXT NOT NULL REFERENCES materials(id),
  PRIMARY KEY (exhibit_id, material_id)
);

CREATE TABLE IF NOT EXISTS exhibit_interactions (
  exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
  interaction_id TEXT NOT NULL REFERENCES interactions(id),
  PRIMARY KEY (exhibit_id, interaction_id)
);

CREATE TABLE IF NOT EXISTS media_assets (
  id TEXT PRIMARY KEY,
  exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  object_key TEXT NOT NULL,
  public_url TEXT,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  file_type TEXT NOT NULL,
  object_key TEXT NOT NULL,
  source_note TEXT,
  embedding vector(1536),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS exhibit_documents (
  exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  PRIMARY KEY (exhibit_id, document_id)
);

CREATE TABLE IF NOT EXISTS exhibit_relations (
  id TEXT PRIMARY KEY,
  source_exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
  target_exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
  relation_type TEXT NOT NULL,
  weight NUMERIC(5, 4) NOT NULL DEFAULT 1.0,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (source_exhibit_id <> target_exhibit_id)
);

CREATE INDEX IF NOT EXISTS idx_exhibits_project_id ON exhibits(project_id);
CREATE INDEX IF NOT EXISTS idx_exhibits_theme_id ON exhibits(theme_id);
CREATE INDEX IF NOT EXISTS idx_exhibits_supplier_id ON exhibits(supplier_id);
CREATE INDEX IF NOT EXISTS idx_exhibit_relations_source ON exhibit_relations(source_exhibit_id);
CREATE INDEX IF NOT EXISTS idx_exhibit_relations_target ON exhibit_relations(target_exhibit_id);
