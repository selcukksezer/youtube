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
        # Schema migration check for existing tables missing error_message
        cursor.execute("PRAGMA table_info(videos)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "error_message" not in columns:
            try:
                cursor.execute("ALTER TABLE videos ADD COLUMN error_message TEXT")
            except Exception:
                pass

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
        # Create helpful indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenes_video_id ON scenes(video_id)")
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
                        error_message: Optional[str] = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE videos
            SET status = ?, filename = ?, duration_seconds = ?, size_mb = ?, error_message = ?
            WHERE id = ?
        """, (status, filename, duration_seconds, size_mb, error_message, video_id))
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

# Initial schema creation on module load
init_db()

if __name__ == "__main__":
    print(f"Database initialized and verified at {DB_PATH}")

