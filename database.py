"""
SQLite Database Persistence Layer for Shorts Video Creators (shorts.db)
Architecturally optimized with WAL mode, foreign key constraints, busy timeout, error tracking, and modular repositories.
"""
import os
import sqlite3
from typing import Optional
import config

# SHORTS_DB_PATH lets Docker keep the DB on the persisted ./data volume
DB_PATH = os.getenv("SHORTS_DB_PATH") or os.path.join(config.BASE_DIR, "shorts.db")
BACKUP_DIR = os.path.join(config.BASE_DIR, "data", "backups")
_blocklist_cache: Optional[set] = None


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15.0, factory=_ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


from db.channels_scripts_repo import (
    _env_blocklist_entries,
    _seed_stock_blocklist,
    refresh_stock_blocklist_cache,
    get_stock_blocklist_keys,
    add_stock_blocklist,
    is_stock_blocklisted,
    source_asset_was_used,
    record_source_asset,
    save_managed_channel,
    get_managed_channel,
    list_managed_channels,
    update_managed_channel_status,
    save_generated_script,
    get_recent_scripts,
    get_script_history_detailed,
)
from db.videos_repo import (
    add_video_record,
    update_video_status,
    save_scenes,
    get_recent_videos,
    get_video_by_id,
    update_share_decision,
    delete_video_by_id,
    delete_video_by_filename,
    get_video_stats,
    get_ops_dashboard_snapshot,
    update_video_published_url,
    record_published_video,
)
from db.projects_repo import (
    create_project,
    get_project,
    update_project,
    list_projects,
    create_render_job,
    get_render_job,
    _insert_render_job_event,
    append_render_job_event,
    list_render_job_events,
    update_render_job,
    cleanup_stale_tasks,
)
from db.backup_service import (
    _BACKUP_MAGIC,
    _xor_stream,
    encrypted_db_backup,
    decrypt_db_backup,
    maybe_schedule_encrypted_db_backup,
)


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
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
            """
        )
        # Schema migration check for existing tables missing columns
        cursor.execute("PRAGMA table_info(videos)")
        columns = [row["name"] for row in cursor.fetchall()]
        for col_name, col_def in (
            ("error_message", "TEXT"),
            ("seo_json", "TEXT"),
            ("proof_path", "TEXT"),
            ("channel_slug", "TEXT DEFAULT 'default'"),
            ("share_decision", "TEXT"),
            ("youtube_url", "TEXT"),
        ):
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE videos ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass

        cursor.execute(
            """
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
            """
        )

        # Item 55: Multi-channel storage
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT UNIQUE NOT NULL,
                token_path TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Items 70, 78: Batch job tracking
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                niche TEXT DEFAULT '1_news_flash',
                language TEXT DEFAULT 'tr',
                status TEXT DEFAULT 'queued',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # V2 production workflow: durable project and render-job identity.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                niche TEXT DEFAULT '1_news_flash',
                language TEXT DEFAULT 'tr',
                status TEXT DEFAULT 'draft',
                plan_json TEXT,
                settings_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS render_jobs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                status TEXT DEFAULT 'queued',
                percent INTEGER DEFAULT 0,
                step TEXT DEFAULT 'Hazır',
                output_url TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS render_job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES render_jobs(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_render_job_events_job_id_id
            ON render_job_events(job_id, id)
            """
        )

        # Anti-Detect & 5-Rule Compliant Managed Channels (Items 1-70, 28)
        cursor.execute(
            """
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
            """
        )
        cursor.execute("PRAGMA table_info(managed_channels)")
        m_cols = [row["name"] for row in cursor.fetchall()]
        for col_name, col_def in (
            ("warmup_cycles", "INTEGER DEFAULT 0"),
            ("warmup_started_at", "TIMESTAMP"),
            ("recovery_email", "TEXT"),
            ("phone_number", "TEXT"),
            ("phone_type", "TEXT DEFAULT 'physical'"),
        ):
            if col_name not in m_cols:
                try:
                    cursor.execute(f"ALTER TABLE managed_channels ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass

        # Items 1, 57: RSS feeds
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rss_feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                last_checked_at TIMESTAMP
            )
            """
        )

        # Source history is intentionally independent from output videos: deleting a render
        # must never make its downloaded stock asset eligible again.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS source_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL UNIQUE,
                source_url TEXT,
                content_hash TEXT,
                source_name TEXT,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Create helpful indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenes_video_id ON scenes(video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_batch_status ON batch_jobs(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_assets_hash ON source_assets(content_hash)")

        # P2-24 / Item 447: contributor & asset ID copyright blocklist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_blocklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_key TEXT NOT NULL UNIQUE,
                block_type TEXT NOT NULL DEFAULT 'id',
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_blocklist_key ON stock_blocklist(block_key)")
        _seed_stock_blocklist(cursor)

        # Bölüm 8.1 / Madde 120: SQLite Tabanlı Çapraz Senaryo Özgünlük Doğrulaması
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_slug TEXT DEFAULT 'default',
                title TEXT,
                keyword TEXT,
                script_text TEXT NOT NULL,
                script_hash TEXT UNIQUE,
                niche_id TEXT,
                word_count INTEGER,
                similarity_score REAL DEFAULT 0.0,
                status TEXT DEFAULT 'approved',
                video_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_scripts_channel ON generated_scripts(channel_slug, created_at DESC)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scripts_hash ON generated_scripts(script_hash)")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
            """
        )
        cursor.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (?, ?)",
            ("2026_10_top100_resilience", "WAL concurrency and Top-100 architecture schema baseline"),
        )

        conn.commit()


# Initial schema creation on module load
init_db()
try:
    maybe_schedule_encrypted_db_backup()
except Exception:
    pass

if __name__ == "__main__":
    import sys as _sys

    # python database.py backup            -> write encrypted backup now
    # python database.py restore X.db.enc Y.db  -> decrypt backup to Y.db
    _args = _sys.argv[1:]
    if _args[:1] == ["backup"]:
        print(encrypted_db_backup() or "no database file to back up")
    elif _args[:1] == ["restore"] and len(_args) >= 3:
        print(decrypt_db_backup(_args[1], _args[2]))
    else:
        print(f"Database initialized and verified at {DB_PATH}")
        print("Usage: python database.py [backup | restore <file.db.enc> <out.db>]")
