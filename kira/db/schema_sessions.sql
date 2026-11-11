-- db_2: sesiones de Strands y memoria de largo plazo
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    session_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_agents (
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    state_json TEXT NOT NULL,
    conversation_manager_state_json TEXT NOT NULL,
    internal_state_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (session_id, agent_id)
);

CREATE TABLE IF NOT EXISTS session_messages (
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    message_json TEXT NOT NULL,
    redact_message_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (session_id, agent_id, message_id),
    FOREIGN KEY (session_id, agent_id)
        REFERENCES session_agents(session_id, agent_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memory_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory_entries(scope);
