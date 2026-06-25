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
        WHERE endpoint NOT IN ('/latency/health', '/', '/docs', '/openapi.json', '/redoc', '/latency/dashboard', '/latency/summary', '/latency/dashboard/detail')
        GROUP BY endpoint, method
        ORDER BY avg_ms DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_degradation(endpoint, method):
    conn = get_connection()

    recent = conn.execute("""
        SELECT AVG(response_time_ms) as avg_ms, COUNT(*) as sample_size
        FROM requests
        WHERE endpoint = ? AND method = ?
        AND timestamp > datetime('now', '-10 minutes')
    """, (endpoint, method)).fetchone()

    baseline = conn.execute("""
        SELECT AVG(response_time_ms) as avg_ms, COUNT(*) as sample_size
        FROM requests
        WHERE endpoint = ? AND method = ?
        AND timestamp > datetime('now', '-24 hours')
    """, (endpoint, method)).fetchone()

    conn.close()

    if not recent["avg_ms"] or not baseline["avg_ms"]:
        return None

    change_pct = ((recent["avg_ms"] - baseline["avg_ms"]) / baseline["avg_ms"]) * 100

    return {
        "recent_avg_ms": round(recent["avg_ms"], 2),
        "baseline_avg_ms": round(baseline["avg_ms"], 2),
        "change_pct": round(change_pct, 2),
        "recent_sample_size": recent["sample_size"],
        "baseline_sample_size": baseline["sample_size"]
    }


def get_hourly_trend(endpoint, method):
    conn = get_connection()
    rows = conn.execute("""
        SELECT 
            strftime('%Y-%m-%d %H:00', timestamp) as hour,
            AVG(response_time_ms) as avg_ms,
            COUNT(*) as request_count,
            SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) as error_count
        FROM requests
        WHERE endpoint = ? AND method = ?
        AND timestamp > datetime('now', '-24 hours')
        GROUP BY hour
        ORDER BY hour ASC
    """, (endpoint, method)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_error_rate_over_time(endpoint, method):
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            strftime('%Y-%m-%d %H:00', timestamp) as hour,
            COUNT(*) as total,
            SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) as errors,
            ROUND(100.0 * SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate_pct
        FROM requests
        WHERE endpoint = ? AND method = ?
        AND timestamp > datetime('now', '-24 hours')
        GROUP BY hour
        ORDER BY hour ASC
    """, (endpoint, method)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_endpoints():
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT endpoint, method FROM requests
        WHERE endpoint NOT IN ('/latency/health', '/', '/docs', '/openapi.json', '/redoc', '/latency/dashboard', '/latency/summary', '/latency/dashboard/detail')
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]


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