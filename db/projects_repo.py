"""
V2 Production Projects, Render Jobs, Event Ledger, and Crash Recovery Repository.
"""
import json
import os
from typing import Any, Dict, List, Optional
import config
import database


def _conn():
    return database.get_connection()


def create_project(
    project_id: str, title: str, niche: str = "1_news_flash", language: str = "tr"
) -> Dict[str, Any]:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO projects (id, title, niche, language) VALUES (?, ?, ?, ?)",
            (project_id, title, niche, language),
        )
        conn.commit()
    return get_project(project_id) or {}


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None


def update_project(
    project_id: str,
    *,
    status: Optional[str] = None,
    plan_json: Optional[str] = None,
    settings_json: Optional[str] = None,
) -> bool:
    fields, values = [], []
    for name, value in (
        ("status", status),
        ("plan_json", plan_json),
        ("settings_json", settings_json),
    ):
        if value is not None:
            fields.append(f"{name} = ?")
            values.append(value)
    if not fields:
        return bool(get_project(project_id))
    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(project_id)
    with _conn() as conn:
        cur = conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        return cur.rowcount > 0


def list_projects(limit: int = 50) -> List[Dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC LIMIT ?", (int(limit),)
        ).fetchall()
        return [dict(row) for row in rows]


def _insert_render_job_event(conn, job_id: str, event_type: str, payload: Any) -> None:
    payload_json = json.dumps(payload, ensure_ascii=False)
    conn.execute(
        """INSERT INTO render_job_events (job_id, event_type, payload_json)
           VALUES (?, ?, ?)""",
        (job_id, event_type, payload_json),
    )


def create_render_job(job_id: str, project_id: str) -> Dict[str, Any]:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO render_jobs (id, project_id) VALUES (?, ?)",
            (job_id, project_id),
        )
        _insert_render_job_event(conn, job_id, "status", {"status": "queued"})
        conn.commit()
    return get_render_job(job_id) or {}


def get_render_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM render_jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def append_render_job_event(job_id: str, event_type: str, payload: Any) -> int:
    if not event_type:
        raise ValueError("Render job event type cannot be empty.")
    with _conn() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM render_jobs WHERE id = ?",
            (job_id,),
        )
        if cursor.fetchone() is None:
            raise ValueError(f"Render job not found: {job_id}")
        _insert_render_job_event(conn, job_id, event_type, payload)
        event_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    return event_id


def list_render_job_events(
    job_id: str, *, after_id: int = 0, limit: int = 200
) -> List[Dict[str, Any]]:
    cursor_id = max(0, int(after_id))
    page_size = max(1, min(int(limit), 500))
    with _conn() as conn:
        rows = conn.execute(
            """SELECT id, job_id, event_type, payload_json, created_at
               FROM render_job_events
               WHERE job_id = ? AND id > ?
               ORDER BY id ASC LIMIT ?""",
            (job_id, cursor_id, page_size),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "job_id": row["job_id"],
            "event_type": row["event_type"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def update_render_job(
    job_id: str,
    *,
    status: Optional[str] = None,
    percent: Optional[int] = None,
    step: Optional[str] = None,
    output_url: Optional[str] = None,
    error_message: Optional[str] = None,
) -> bool:
    fields, values = [], []
    for name, value in (
        ("status", status),
        ("percent", percent),
        ("step", step),
        ("output_url", output_url),
        ("error_message", error_message),
    ):
        if value is not None:
            fields.append(f"{name} = ?")
            values.append(value)
    if not fields:
        return bool(get_render_job(job_id))
    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(job_id)
    with _conn() as conn:
        existing = conn.execute(
            "SELECT status FROM render_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if existing is None:
            return False
        cur = conn.execute(f"UPDATE render_jobs SET {', '.join(fields)} WHERE id = ?", values)
        if cur.rowcount and status is not None and status != existing["status"]:
            event_payload = {"status": status}
            for key, value in (
                ("percent", percent),
                ("step", step),
                ("output_url", output_url),
                ("error_message", error_message),
            ):
                if value is not None:
                    event_payload[key] = value
            _insert_render_job_event(conn, job_id, "status", event_payload)
        conn.commit()
        return cur.rowcount > 0


def cleanup_stale_tasks():
    """Marks in-flight tasks as failed when the server restarts or crashes, recovering completed outputs if found."""
    restart_error = "Sunucu yeniden başlatıldı; render işi tamamlanamadı."
    output_dir = getattr(config, "OUTPUT_DIR", None) or "output"
    with _conn() as conn:
        try:
            processing_videos = conn.execute(
                "SELECT id, keyword, filename FROM videos WHERE status = 'processing'"
            ).fetchall()
            for vid_id, kw, fn in processing_videos:
                recovered_path = None
                if fn and os.path.exists(fn) and os.path.getsize(fn) > 10000:
                    recovered_path = fn
                elif os.path.isdir(output_dir):
                    for candidate in os.listdir(output_dir):
                        if candidate.endswith(".mp4") and str(vid_id) in candidate:
                            full_p = os.path.join(output_dir, candidate)
                            if os.path.getsize(full_p) > 10000:
                                recovered_path = full_p
                                break
                if recovered_path:
                    conn.execute(
                        "UPDATE videos SET status = 'completed', filename = ?, error_message = NULL WHERE id = ?",
                        (recovered_path, vid_id),
                    )
        except Exception:
            pass

        stale_render_jobs = conn.execute(
            """
            SELECT id FROM render_jobs
            WHERE status IN ('queued', 'rendering', 'cancelling')
            """
        ).fetchall()
        conn.execute(
            """
            UPDATE videos
            SET status = 'failed',
                error_message = 'Sunucu yeniden başlatıldı veya işlem beklenmedik şekilde sonlandı.'
            WHERE status = 'processing'
            """
        )
        conn.execute(
            """
            UPDATE projects
            SET status = 'ready_to_render', updated_at = CURRENT_TIMESTAMP
            WHERE status = 'rendering'
              AND EXISTS (
                  SELECT 1 FROM render_jobs
                  WHERE render_jobs.project_id = projects.id
                    AND render_jobs.status IN ('queued', 'rendering', 'cancelling')
              )
            """
        )
        conn.execute(
            """
            UPDATE render_jobs
            SET status = 'failed',
                step = 'Başarısız',
                error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE status IN ('queued', 'rendering', 'cancelling')
            """,
            (restart_error,),
        )
        for row in stale_render_jobs:
            _insert_render_job_event(
                conn,
                row["id"],
                "status",
                {
                    "status": "failed",
                    "step": "Başarısız",
                    "error_message": restart_error,
                },
            )
        conn.commit()
