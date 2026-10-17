"""
Video, scene, published link, and local ops statistics repository functions.
"""
from typing import Any, Dict, List, Optional
import database


def _conn():
    return database.get_connection()


def add_video_record(
    keyword: str,
    language: str = "en",
    ai_provider: str = "Gemini",
    channel_slug: str = "default",
) -> int:
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO videos (keyword, title, status, language, ai_provider, channel_slug)
            VALUES (?, ?, 'processing', ?, ?, ?)
            """,
            (keyword, keyword, language, ai_provider, channel_slug or "default"),
        )
        conn.commit()
        return cursor.lastrowid


def update_video_status(
    video_id: int,
    status: str,
    filename: Optional[str] = None,
    duration_seconds: float = 0.0,
    size_mb: float = 0.0,
    error_message: Optional[str] = None,
    seo_json: Optional[str] = None,
    proof_path: Optional[str] = None,
):
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE videos
            SET status = ?, filename = ?, duration_seconds = ?, size_mb = ?, error_message = ?,
                seo_json = COALESCE(?, seo_json), proof_path = COALESCE(?, proof_path)
            WHERE id = ?
            """,
            (status, filename, duration_seconds, size_mb, error_message, seo_json, proof_path, video_id),
        )
        conn.commit()


def save_scenes(video_id: int, scenes: List[Dict[str, Any]]):
    with _conn() as conn:
        cursor = conn.cursor()
        for idx, s in enumerate(scenes, 1):
            sq_list = s.get("search_queries")
            sq = sq_list[0] if (sq_list and len(sq_list) > 0) else s.get("search_query", "")
            cursor.execute(
                """
                INSERT INTO scenes (video_id, scene_number, scene_description, search_query, duration, narration)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (video_id, idx, s.get("scene_description", ""), sq, s.get("duration", 0), s.get("narration", "")),
            )
        conn.commit()


def get_recent_videos(limit: int = 50) -> List[Dict[str, Any]]:
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM videos ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_video_by_id(video_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single video record by ID."""
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM videos WHERE id = ?", (int(video_id),))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_share_decision(video_id: int, decision: str) -> bool:
    """decision: 'keep' (manual upload) or 'discarded'."""
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE videos SET share_decision = ? WHERE id = ?",
            (decision, int(video_id)),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_video_by_id(video_id: int) -> bool:
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM videos WHERE id = ?", (int(video_id),))
        conn.commit()
        return cursor.rowcount > 0


def delete_video_by_filename(filename: str) -> bool:
    """Deletes database entry when a video file is deleted."""
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM videos WHERE filename = ?", (filename,))
        conn.commit()
        return cursor.rowcount > 0


def get_video_stats() -> Dict[str, Any]:
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM videos WHERE status = 'completed'")
        completed = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(duration_seconds) FROM videos WHERE status = 'completed'")
        total_sec = cursor.fetchone()[0] or 0.0
        return {
            "total_completed": completed,
            "total_minutes": round(total_sec / 60.0, 1),
        }


def get_ops_dashboard_snapshot() -> Dict[str, Any]:
    """
    R10 #100: Local ops dashboard — renders, channels, advisory RPM (not live YT Analytics).
    """
    stats = get_video_stats()
    channels = []
    try:
        with _conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT handle, channel_name, niche, status, health_score FROM managed_channels ORDER BY id DESC LIMIT 50"
                )
                for row in cursor.fetchall():
                    channels.append(
                        {
                            "handle": row[0],
                            "channel_name": row[1],
                            "niche": row[2],
                            "status": row[3],
                            "health_score": row[4],
                            "views": None,
                            "subscribers": None,
                            "estimated_revenue_usd": None,
                            "metrics_note": "Live YT Analytics API not wired — fill manually or connect OAuth later.",
                        }
                    )
            except Exception:
                pass
            try:
                cursor.execute("SELECT status, COUNT(*) FROM videos GROUP BY status")
                by_status = {r[0]: r[1] for r in cursor.fetchall()}
            except Exception:
                by_status = {}
    except Exception:
        by_status = {}
    try:
        from scenes.plan_linter import build_scenario_quality_dashboard_metrics
        scenario_quality = build_scenario_quality_dashboard_metrics(recent_limit=15)
    except Exception:
        scenario_quality = {"total_evaluated": 0, "usable_rate_pct": 100.0, "issue_breakdown": {}}
    return {
        "rule": "r10_100_ops_dashboard",
        "local_renders": stats,
        "videos_by_status": by_status,
        "managed_channels": channels,
        "channel_count": len(channels),
        "scenario_quality": scenario_quality,
        "monetization_advisory": {
            "rpm_note": "Use niche rpm_tier from niche_templates as planning hint only.",
            "live_revenue": False,
        },
    }


def update_video_published_url(video_id: int, youtube_url: str) -> bool:
    """
    Chapter 9.1: Updates the published YouTube/Shorts URL for an existing video record.
    Sets status='published'.
    """
    if not video_id or not youtube_url:
        return False
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE videos SET youtube_url = ?, status = 'published' WHERE id = ?",
            (str(youtube_url).strip(), int(video_id)),
        )
        conn.commit()
        return cursor.rowcount > 0


def record_published_video(
    title: str,
    youtube_url: str,
    *,
    keyword: str = "",
    channel_slug: str = "default",
    filename: str = "",
    duration_seconds: float = 0.0,
    size_mb: float = 0.0,
) -> int:
    """
    Chapter 9.1: Inserts a new published video record directly into SQLite with its YouTube link.
    """
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO videos (keyword, title, status, filename, duration_seconds, size_mb, channel_slug, youtube_url)
            VALUES (?, ?, 'published', ?, ?, ?, ?, ?)
            """,
            (
                keyword or title,
                str(title or "Short Video").strip(),
                filename,
                float(duration_seconds),
                float(size_mb),
                channel_slug or "default",
                str(youtube_url).strip(),
            ),
        )
        conn.commit()
        return cursor.lastrowid
