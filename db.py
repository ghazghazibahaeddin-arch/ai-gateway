import sqlite3
import json
from datetime import datetime
from typing import Any

DB_PATH = "gateway.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            pii_count INTEGER DEFAULT 0,
            pii_types TEXT DEFAULT '[]',
            latency_ms INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS pii_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            score REAL NOT NULL,
            original_length INTEGER NOT NULL,
            FOREIGN KEY (request_id) REFERENCES requests(id)
        );
    """)
    conn.commit()
    conn.close()


def log_request(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cost: float,
    pii_findings: list[dict],
    latency_ms: int,
):
    conn = get_conn()
    try:
        pii_types = list({f["entity_type"] for f in pii_findings})
        timestamp = datetime.utcnow().isoformat()

        cur = conn.execute(
            """INSERT INTO requests (timestamp, model, prompt_tokens, completion_tokens,
               total_tokens, cost_usd, pii_count, pii_types, latency_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                timestamp,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                cost,
                len(pii_findings),
                json.dumps(pii_types),
                latency_ms,
            ),
        )
        request_id = cur.lastrowid

        for finding in pii_findings:
            conn.execute(
                """INSERT INTO pii_events (request_id, timestamp, entity_type, score, original_length)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    request_id,
                    timestamp,
                    finding["entity_type"],
                    finding["score"],
                    finding["original_length"],
                ),
            )

        conn.commit()
    finally:
        conn.close()


def get_stats() -> dict:
    conn = get_conn()
    try:
        row = conn.execute(
            """SELECT
                COUNT(*) as total_requests,
                COALESCE(SUM(cost_usd), 0) as total_cost,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(pii_count), 0) as total_pii_detections,
                COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
                COUNT(CASE WHEN pii_count > 0 THEN 1 END) as requests_with_pii
            FROM requests"""
        ).fetchone()

        model_rows = conn.execute(
            """SELECT model, COUNT(*) as count, SUM(cost_usd) as cost, SUM(total_tokens) as tokens
               FROM requests GROUP BY model ORDER BY count DESC"""
        ).fetchall()

        daily_rows = conn.execute(
            """SELECT DATE(timestamp) as date,
                      COUNT(*) as requests,
                      SUM(cost_usd) as cost,
                      SUM(total_tokens) as tokens
               FROM requests
               WHERE timestamp >= DATE('now', '-7 days')
               GROUP BY DATE(timestamp)
               ORDER BY date ASC"""
        ).fetchall()

        pii_type_rows = conn.execute(
            """SELECT entity_type, COUNT(*) as count
               FROM pii_events
               GROUP BY entity_type
               ORDER BY count DESC
               LIMIT 10"""
        ).fetchall()

        return {
            "total_requests": row["total_requests"],
            "total_cost": round(row["total_cost"], 6),
            "total_tokens": row["total_tokens"],
            "total_pii_detections": row["total_pii_detections"],
            "avg_latency_ms": round(row["avg_latency_ms"], 1),
            "requests_with_pii": row["requests_with_pii"],
            "by_model": [
                {
                    "model": r["model"],
                    "count": r["count"],
                    "cost": round(r["cost"], 6),
                    "tokens": r["tokens"],
                }
                for r in model_rows
            ],
            "daily": [
                {
                    "date": r["date"],
                    "requests": r["requests"],
                    "cost": round(r["cost"], 6),
                    "tokens": r["tokens"],
                }
                for r in daily_rows
            ],
            "pii_by_type": [
                {"type": r["entity_type"], "count": r["count"]}
                for r in pii_type_rows
            ],
        }
    finally:
        conn.close()


def get_risk_logs(limit: int = 50, offset: int = 0) -> dict:
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT r.id, r.timestamp, r.model, r.total_tokens, r.cost_usd,
                      r.pii_count, r.pii_types, r.latency_ms
               FROM requests r
               WHERE r.pii_count > 0
               ORDER BY r.timestamp DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM requests WHERE pii_count > 0"
        ).fetchone()[0]

        return {
            "items": [
                {
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "model": r["model"],
                    "total_tokens": r["total_tokens"],
                    "cost_usd": round(r["cost_usd"], 6),
                    "pii_count": r["pii_count"],
                    "pii_types": json.loads(r["pii_types"]),
                    "latency_ms": r["latency_ms"],
                }
                for r in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()
