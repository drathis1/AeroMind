CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    event_id TEXT,
    context JSONB DEFAULT '{}',
    open_escalation BOOLEAN DEFAULT FALSE,
    reroute_complete BOOLEAN DEFAULT FALSE,
    dg_accepted BOOLEAN DEFAULT FALSE,
    autonomous_commits INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE orchestrator_events (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (event_id)
);

CREATE TABLE agent_runs (
    id BIGSERIAL PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    input JSONB DEFAULT '{}',
    output JSONB DEFAULT '{}',
    terminal BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE human_gates (
    id BIGSERIAL PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    gate_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    summary JSONB DEFAULT '{}',
    rationale TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE regulatory_chunks (
    id TEXT PRIMARY KEY,
    instrument TEXT,
    jurisdiction TEXT,
    body TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB DEFAULT '{}'
);

-- Create ANN index after loading chunks; ivfflat requires analyze/data

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    workflow_id TEXT,
    actor TEXT NOT NULL,
    decision_payload JSONB NOT NULL DEFAULT '{}',
    evidence_refs JSONB DEFAULT '[]',
    outcome TEXT NOT NULL,
    prev_hash TEXT,
    entry_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE governance_violations (
    id BIGSERIAL PRIMARY KEY,
    workflow_id TEXT,
    agent_id TEXT,
    tool_name TEXT,
    detail JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE injection_attempts (
    id BIGSERIAL PRIMARY KEY,
    workflow_id TEXT,
    agent_id TEXT,
    source TEXT,
    redacted_excerpt TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE llm_judge_evaluations (
    id BIGSERIAL PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    mandatory_human_review BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_workflow ON audit_log(workflow_id);
CREATE INDEX idx_agent_runs_wf ON agent_runs(workflow_id);
