import sqlite3
import os
from datetime import datetime
import pickle

DB_PATH = os.path.join(os.path.dirname(__file__), "metrics.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL,
            method TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            response_time_ms REAL NOT NULL,
            timestamp TEXT NOT NULL)
        """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS digest_snapshots (
        method TEXT,
        endpoint TEXT,
        blob BLOB,
         PRIMARY KEY (method, endpoint))
    """)
    conn.commit()
    conn.close()


def insert_request(endpoint, method, status_code, response_time_ms):
    conn = get_connection()
    conn.execute("""
        INSERT INTO requests (endpoint, method, status_code, response_time_ms, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (endpoint, method, status_code, response_time_ms, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_slowest_endpoints(limit=5):
    conn = get_connection()
    rows = conn.execute("""
        SELECT endpoint, method,
               AVG(response_time_ms) as avg_ms,
               COUNT(*) as total_requests,
               SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) as error_count
        FROM requests
        WHERE endpoint NOT IN ('/latency/health', '/', '/docs', '/openapi.json', '/redoc')
        GROUP BY endpoint, method
        ORDER BY avg_ms DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_degradation(endpoint, method):
    conn = get_connection()
    
    recent = conn.execute("""
        SELECT AVG(response_time_ms) as avg_ms FROM (
            SELECT response_time_ms FROM requests
            WHERE endpoint = ? AND method = ?
            ORDER BY timestamp DESC LIMIT 3
        )
    """, (endpoint, method)).fetchone()["avg_ms"]

    baseline = conn.execute("""
        SELECT AVG(response_time_ms) as avg_ms FROM (
            SELECT response_time_ms FROM requests
            WHERE endpoint = ? AND method = ?
            ORDER BY timestamp DESC LIMIT 5
        )
    """, (endpoint, method)).fetchone()["avg_ms"]

    conn.close()

    if not recent or not baseline:
        return None

    change_pct = ((recent - baseline) / baseline) * 100
    return {
        "recent_avg_ms": round(recent, 2),
        "baseline_avg_ms": round(baseline, 2),
        "change_pct": round(change_pct, 2)
    }

#tdigest persistence 
#save digest as a binary blob using pickle
def save_digests(digest_map):
    conn = get_connection()
    for (method, endpoint), digest in digest_map.items():
        conn.execute("""
            INSERT OR REPLACE INTO digest_snapshots (method, endpoint, blob)
            VALUES (?, ?, ?)
        """, (method, endpoint, pickle.dumps(digest)))
    conn.commit()
    conn.close()


#fetch and load digest blob 
def load_digests():
    conn = get_connection()
    # fetch all saved rows from the persistence table
    rows = conn.execute("SELECT method, endpoint, blob FROM digest_snapshots").fetchall()
    conn.close()
    
    digest_map = {}  # temporary local dict, not the module-level one
    for row in rows:
        key = (row["method"], row["endpoint"])  # rebuild the tuple key
        digest_map[key] = pickle.loads(row["blob"])  # unpickle blob back into TDigest object
    
    return digest_map  # return the populated dict