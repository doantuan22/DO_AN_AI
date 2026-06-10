CREATE TABLE IF NOT EXISTS path_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    start_node_id TEXT NOT NULL,
    start_node_name TEXT NOT NULL,
    goal_node_id TEXT NOT NULL,
    goal_node_name TEXT NOT NULL,
    distance_m REAL NOT NULL,
    path_node_ids TEXT NOT NULL,
    path_names TEXT NOT NULL,
    visited_count INTEGER NOT NULL DEFAULT 0,
    elapsed_ms REAL NOT NULL DEFAULT 0
);
