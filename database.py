"""
SQLite Database Persistence Layer for Shorts Video Creators (shorts.db)
Architecturally optimized with WAL mode, foreign key constraints, error tracking and cleanup.
"""
import os, sqlite3, time
from typing import List, Dict, Any, Optional
import config

DB_PATH = os.path.join(config.BASE_DIR, "shorts.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                title TEXT,
                status TEXT DEFAULT 'pending',
                filename TEXT,
                duration_seconds REAL DEFAULT 0,
                size_mb REAL DEFAULT 0,
                ai_provider TEXT,
                language TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Schema migration check for existing tables missing columns
        cursor.execute("PRAGMA table_info(videos)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "error_message" not in columns:
            try: cursor.execute("ALTER TABLE videos ADD COLUMN error_message TEXT")
            except Exception: pass
        if "seo_json" not in columns:
            try: cursor.execute("ALTER TABLE videos ADD COLUMN seo_json TEXT")
            except Exception: pass
        if "proof_path" not in columns:
            try: cursor.execute("ALTER TABLE videos ADD COLUMN proof_path TEXT")
            except Exception: pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER NOT NULL,
                scene_number INTEGER,
                scene_description TEXT,
                search_query TEXT,
                duration REAL,
                narration TEXT,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
            )
        """)

        # Item 55: Multi-channel storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT UNIQUE NOT NULL,
                token_path TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Items 70, 78: Batch job tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                niche TEXT DEFAULT '1_news_flash',
                language TEXT DEFAULT 'tr',
                status TEXT DEFAULT 'queued',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Anti-Detect & 5-Rule Compliant Managed Channels (Items 1-70, 28)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS managed_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_url TEXT NOT NULL UNIQUE,
                handle TEXT NOT NULL,
                channel_name TEXT,
                niche TEXT DEFAULT 'Genel Shorts',
                proxy_url TEXT,
                profile_id TEXT NOT NULL,
                status TEXT DEFAULT 'resting',
                health_score INTEGER DEFAULT 100,
                resting_until TIMESTAMP,
                warmup_completed_at TIMESTAMP,
                warmup_started_at TIMESTAMP,
                warmup_cycles INTEGER DEFAULT 0,
                last_upload_at TIMESTAMP,
                config_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("PRAGMA table_info(managed_channels)")
        m_cols = [row["name"] for row in cursor.fetchall()]
        if "warmup_cycles" not in m_cols:
            try: cursor.execute("ALTER TABLE managed_channels ADD COLUMN warmup_cycles INTEGER DEFAULT 0")
            except Exception: pass
        if "warmup_started_at" not in m_cols:
            try: cursor.execute("ALTER TABLE managed_channels ADD COLUMN warmup_started_at TIMESTAMP")
            except Exception: pass
        if "recovery_email" not in m_cols:
            try: cursor.execute("ALTER TABLE managed_channels ADD COLUMN recovery_email TEXT")
            except Exception: pass
        if "phone_number" not in m_cols:
            try: cursor.execute("ALTER TABLE managed_channels ADD COLUMN phone_number TEXT")
            except Exception: pass
        if "phone_type" not in m_cols:
            try: cursor.execute("ALTER TABLE managed_channels ADD COLUMN phone_type TEXT DEFAULT 'physical'")
            except Exception: pass



        # Items 1, 57: RSS feeds
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rss_feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                last_checked_at TIMESTAMP
            )
        """)

        # Source history is intentionally independent from output videos: deleting a render
        # must never make its downloaded stock asset eligible again.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL UNIQUE,
                source_url TEXT,
                content_hash TEXT,
                source_name TEXT,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create helpful indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenes_video_id ON scenes(video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_batch_status ON batch_jobs(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_assets_hash ON source_assets(content_hash)")
        conn.commit()

def source_asset_was_used(source_key: str, content_hash: Optional[str] = None) -> bool:
    """Checks persistent source history, which survives video deletion and restarts."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM source_assets WHERE source_key = ? OR (? IS NOT NULL AND content_hash = ?) LIMIT 1",
            (source_key, content_hash, content_hash)
        ).fetchone()
    return row is not None

def record_source_asset(source_key: str, source_url: str = "", content_hash: str = "", source_name: str = "") -> None:
    """Records a selected source once; conflicts preserve the original historical record."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO source_assets (source_key, source_url, content_hash, source_name) VALUES (?, ?, ?, ?)",
            (source_key, source_url, content_hash, source_name)
        )
        conn.commit()

def cleanup_stale_tasks():
    """Recovers any tasks left in 'processing' state when server restarts or after crash."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE videos 
                SET status = 'failed', error_message = 'Sunucu yeniden başlatıldı veya işlem beklenmedik şekilde sonlandı.' 
                WHERE status = 'processing'
            """)
            conn.commit()
    except Exception:
        pass

def add_video_record(keyword: str, language: str = "en", ai_provider: str = "Gemini") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO videos (keyword, title, status, language, ai_provider)
            VALUES (?, ?, 'processing', ?, ?)
        """, (keyword, keyword, language, ai_provider))
        conn.commit()
        return cursor.lastrowid

def update_video_status(video_id: int, status: str, filename: Optional[str] = None, 
                        duration_seconds: float = 0.0, size_mb: float = 0.0, 
                        error_message: Optional[str] = None,
                        seo_json: Optional[str] = None,
                        proof_path: Optional[str] = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE videos
            SET status = ?, filename = ?, duration_seconds = ?, size_mb = ?, error_message = ?,
                seo_json = COALESCE(?, seo_json), proof_path = COALESCE(?, proof_path)
            WHERE id = ?
        """, (status, filename, duration_seconds, size_mb, error_message, seo_json, proof_path, video_id))
        conn.commit()

def save_scenes(video_id: int, scenes: List[Dict[str, Any]]):
    with get_connection() as conn:
        cursor = conn.cursor()
        for idx, s in enumerate(scenes, 1):
            sq_list = s.get("search_queries")
            sq = sq_list[0] if (sq_list and len(sq_list) > 0) else s.get("search_query", "")
            cursor.execute("""
                INSERT INTO scenes (video_id, scene_number, scene_description, search_query, duration, narration)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (video_id, idx, s.get("scene_description", ""), sq, s.get("duration", 0), s.get("narration", "")))
        conn.commit()

def get_recent_videos(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM videos ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def delete_video_by_filename(filename: str) -> bool:
    """Deletes database entry when a video file is deleted."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM videos WHERE filename = ?", (filename,))
        conn.commit()
        return cursor.rowcount > 0

def get_video_stats() -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM videos WHERE status = 'completed'")
        completed = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(duration_seconds) FROM videos WHERE status = 'completed'")
        total_sec = cursor.fetchone()[0] or 0.0
        return {
            "total_completed": completed,
            "total_minutes": round(total_sec / 60.0, 1)
        }

def save_managed_channel(
    channel_url: str,
    handle: str,
    channel_name: str,
    niche: str = "Genel Shorts",
    proxy_url: Optional[str] = None,
    profile_id: Optional[str] = None,
    status: str = "resting",
    health_score: int = 100,
    resting_until: Optional[str] = None,
    config_json: Optional[str] = None,
    recovery_email: Optional[str] = None,
    phone_number: Optional[str] = None,
    phone_type: str = "physical"
) -> int:
    """Inserts or updates a managed YouTube channel with anti-detect profile."""
    profile_id = profile_id or handle.lstrip("@")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO managed_channels (
                channel_url, handle, channel_name, niche, proxy_url, profile_id,
                status, health_score, resting_until, config_json,
                recovery_email, phone_number, phone_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(channel_url) DO UPDATE SET
                handle = excluded.handle,
                channel_name = excluded.channel_name,
                niche = excluded.niche,
                proxy_url = excluded.proxy_url,
                profile_id = excluded.profile_id,
                status = excluded.status,
                health_score = excluded.health_score,
                resting_until = COALESCE(excluded.resting_until, managed_channels.resting_until),
                config_json = excluded.config_json,
                recovery_email = COALESCE(excluded.recovery_email, managed_channels.recovery_email),
                phone_number = COALESCE(excluded.phone_number, managed_channels.phone_number),
                phone_type = COALESCE(excluded.phone_type, managed_channels.phone_type)
        """, (channel_url, handle, channel_name, niche, proxy_url, profile_id,
              status, health_score, resting_until, config_json,
              recovery_email, phone_number, phone_type))
        conn.commit()
        return cursor.lastrowid


def get_managed_channel(identifier: str) -> Optional[Dict[str, Any]]:
    """Retrieves a managed channel by URL, handle, or ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if str(identifier).isdigit():
            cursor.execute("SELECT * FROM managed_channels WHERE id = ?", (int(identifier),))
        else:
            cursor.execute("SELECT * FROM managed_channels WHERE channel_url = ? OR handle = ?", (identifier, identifier))
        row = cursor.fetchone()
        return dict(row) if row else None

def list_managed_channels() -> List[Dict[str, Any]]:
    """Returns all registered managed channels with health metrics."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM managed_channels ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def update_managed_channel_status(
    channel_id: int,
    status: Optional[str] = None,
    health_score: Optional[int] = None,
    warmup_completed: bool = False,
    last_upload: bool = False,
    increment_cycles: bool = False
):
    """Updates status, score, or timestamps for a managed channel."""
    updates = []
    params = []
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if health_score is not None:
        updates.append("health_score = ?")
        params.append(health_score)
    if warmup_completed:
        updates.append("warmup_completed_at = CURRENT_TIMESTAMP")
        updates.append("warmup_started_at = COALESCE(warmup_started_at, CURRENT_TIMESTAMP)")
    if increment_cycles:
        updates.append("warmup_cycles = COALESCE(warmup_cycles, 0) + 1")
    if last_upload:
        updates.append("last_upload_at = CURRENT_TIMESTAMP")
    
    if not updates:
        return

    params.append(channel_id)

    with get_connection() as conn:
        cursor = conn.cursor()
        sql = f"UPDATE managed_channels SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, tuple(params))
        conn.commit()

# Initial schema creation on module load
init_db()

if __name__ == "__main__":
    print(f"Database initialized and verified at {DB_PATH}")


