-- PWM schema generated from 'Personal World Model' document

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- optional future extension for vectors
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Core identity
CREATE TABLE IF NOT EXISTS users (
  user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS global_identity (
  user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
  core_values JSONB,
  long_term_goals JSONB,
  risk_tolerance FLOAT CHECK (risk_tolerance BETWEEN 0 AND 1),
  personality_baseline JSONB,
  confidence FLOAT DEFAULT 0.8,
  updated_at TIMESTAMP DEFAULT now()
);

-- Entity layer
CREATE TABLE IF NOT EXISTS entities (
  entity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_type TEXT CHECK (entity_type IN ('person', 'project', 'event', 'self')),
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS people (
  person_id UUID PRIMARY KEY REFERENCES entities(entity_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  role_in_life TEXT[],
  traits JSONB,
  communication_style TEXT,
  confidence FLOAT DEFAULT 0.7
);

CREATE TABLE IF NOT EXISTS projects (
  project_id UUID PRIMARY KEY REFERENCES entities(entity_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  domain TEXT,
  goal TEXT,
  status TEXT CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
  started_at DATE,
  ended_at DATE
);

CREATE TABLE IF NOT EXISTS events (
  event_id UUID PRIMARY KEY REFERENCES entities(entity_id) ON DELETE CASCADE,
  event_type TEXT,
  description TEXT,
  occurred_at TIMESTAMP,
  emotional_valence FLOAT CHECK (emotional_valence BETWEEN -1 AND 1)
);

-- Relationship graph
CREATE TABLE IF NOT EXISTS relationships (
  relationship_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  from_entity UUID REFERENCES entities(entity_id) ON DELETE CASCADE,
  to_entity UUID REFERENCES entities(entity_id) ON DELETE CASCADE,
  relationship_type TEXT,
  directionality TEXT CHECK (directionality IN ('directed', 'bidirectional')),
  strength FLOAT CHECK (strength BETWEEN 0 AND 1),
  trust FLOAT CHECK (trust BETWEEN 0 AND 1),
  asymmetry FLOAT CHECK (asymmetry BETWEEN 0 AND 1),
  net_effect FLOAT CHECK (net_effect BETWEEN -1 AND 1),
  confidence FLOAT DEFAULT 0.7,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS relationship_timeline (
  timeline_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  relationship_id UUID REFERENCES relationships(relationship_id) ON DELETE CASCADE,
  state TEXT,
  from_date DATE,
  to_date DATE,
  impact_score FLOAT CHECK (impact_score BETWEEN -1 AND 1)
);

-- Evidence & inference
CREATE TABLE IF NOT EXISTS observations (
  observation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_id UUID REFERENCES entities(entity_id),
  description TEXT,
  source TEXT CHECK (source IN ('conversation', 'event', 'explicit_user_input')),
  timestamp TIMESTAMP DEFAULT now(),
  confidence FLOAT DEFAULT 0.6
);

CREATE TABLE IF NOT EXISTS inferences (
  inference_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_id UUID REFERENCES entities(entity_id),
  inference_type TEXT,
  hypothesis TEXT,
  confidence FLOAT CHECK (confidence BETWEEN 0 AND 1),
  supporting_observations UUID[],
  contradicting_observations UUID[],
  created_at TIMESTAMP DEFAULT now(),
  active BOOLEAN DEFAULT TRUE
);

-- Session & governance
CREATE TABLE IF NOT EXISTS sessions (
  session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  emotional_state JSONB
);

CREATE TABLE IF NOT EXISTS session_summaries (
  session_id UUID REFERENCES sessions(session_id),
  summary TEXT,
  extracted_signals JSONB,
  confidence FLOAT
);

CREATE TABLE IF NOT EXISTS memory_changes (
  change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_id UUID,
  change_type TEXT CHECK (change_type IN ('insert', 'update', 'deprecate')),
  old_value JSONB,
  new_value JSONB,
  confidence FLOAT,
  approved BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT now()
);

-- Indexes and helpers (suggested)
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_people_name ON people(lower(name));
CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_entity);
CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_entity);

-- End of schema
