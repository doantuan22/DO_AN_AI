"""SQLite storage for completed pathfinding runs."""

import json
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional


CREATE_PATH_HISTORY_TABLE_SQL = """
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
"""


@dataclass(frozen=True)
class PathHistoryRecord:
    id: int
    created_at: str
    algorithm: str
    start_node_id: str
    start_node_name: str
    goal_node_id: str
    goal_node_name: str
    distance_m: float
    path_node_ids: List[str]
    path_names: List[str]
    visited_count: int
    elapsed_ms: float

    @property
    def route_text(self) -> str:
        names = self.path_names or self.path_node_ids
        return " -> ".join(names)


class HistoryStore:
    """Small SQLite repository for route history."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize()

    def initialize(self) -> None:
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(CREATE_PATH_HISTORY_TABLE_SQL)

    def add_route(
        self,
        algorithm: str,
        start_node_id: str,
        start_node_name: str,
        goal_node_id: str,
        goal_node_name: str,
        distance_m: float,
        path_node_ids: Iterable[str],
        path_names: Iterable[str],
        visited_count: int,
        elapsed_ms: float,
        ) -> int:
        created_at = datetime.now().isoformat(timespec="seconds")
        with closing(self._connect()) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO path_history (
                        created_at, algorithm,
                        start_node_id, start_node_name,
                        goal_node_id, goal_node_name,
                        distance_m, path_node_ids, path_names,
                        visited_count, elapsed_ms
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at,
                        algorithm,
                        start_node_id,
                        start_node_name,
                        goal_node_id,
                        goal_node_name,
                        float(distance_m),
                        json.dumps(list(path_node_ids), ensure_ascii=False),
                        json.dumps(list(path_names), ensure_ascii=False),
                        int(visited_count),
                        float(elapsed_ms),
                    ),
                )
                return int(cursor.lastrowid)

    def list_routes(self, limit: Optional[int] = None) -> List[PathHistoryRecord]:
        sql = "SELECT * FROM path_history ORDER BY id DESC"
        params: tuple = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (int(limit),)
        with closing(self._connect()) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def delete_route(self, record_id: int) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute("DELETE FROM path_history WHERE id = ?", (int(record_id),))

    def clear(self) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute("DELETE FROM path_history")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> PathHistoryRecord:
        return PathHistoryRecord(
            id=int(row["id"]),
            created_at=str(row["created_at"]),
            algorithm=str(row["algorithm"]),
            start_node_id=str(row["start_node_id"]),
            start_node_name=str(row["start_node_name"]),
            goal_node_id=str(row["goal_node_id"]),
            goal_node_name=str(row["goal_node_name"]),
            distance_m=float(row["distance_m"]),
            path_node_ids=json.loads(row["path_node_ids"]),
            path_names=json.loads(row["path_names"]),
            visited_count=int(row["visited_count"]),
            elapsed_ms=float(row["elapsed_ms"]),
        )
