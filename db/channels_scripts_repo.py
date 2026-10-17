"""
Managed YouTube Channels, Script Originality Ledger, Stock Blocklist, and Source Asset History.
"""
import hashlib
import os
from typing import Any, Dict, List, Optional
import database


def _conn():
    return database.get_connection()


def _env_blocklist_entries() -> List[tuple]:
    """Parse STOCK_BLOCKLIST_IDS and STOCK_BLOCKLIST_CONTRIBUTORS from env."""
    rows = []
    ids_raw = os.getenv("STOCK_BLOCKLIST_IDS", "")
    for token in ids_raw.split(","):
        key = token.strip()
        if key:
            rows.append((key, "id", "env blocklist"))
    contrib_raw = os.getenv("STOCK_BLOCKLIST_CONTRIBUTORS", "")
    for token in contrib_raw.split(","):
        name = token.strip()
        if name:
            rows.append((f"contributor:{name.lower()}", "contributor", "env blocklist"))
    return rows


def _seed_stock_blocklist(cursor) -> None:
    for block_key, block_type, reason in _env_blocklist_entries():
        cursor.execute(
            "INSERT OR IGNORE INTO stock_blocklist (block_key, block_type, reason) VALUES (?, ?, ?)",
            (block_key, block_type, reason),
        )


def refresh_stock_blocklist_cache() -> set:
    with _conn() as conn:
        rows = conn.execute("SELECT block_key FROM stock_blocklist").fetchall()
    database._blocklist_cache = {str(r["block_key"]) for r in rows}
    return database._blocklist_cache


def get_stock_blocklist_keys() -> set:
    if database._blocklist_cache is None:
        return refresh_stock_blocklist_cache()
    return database._blocklist_cache


def add_stock_blocklist(block_key: str, block_type: str = "id", reason: str = "") -> bool:
    key = str(block_key or "").strip()
    if not key:
        return False
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO stock_blocklist (block_key, block_type, reason) VALUES (?, ?, ?)",
            (key, block_type, reason),
        )
        conn.commit()
    refresh_stock_blocklist_cache()
    return True


def is_stock_blocklisted(
    source_key: str = "",
    asset_id: str = "",
    contributor: str = "",
) -> bool:
    """True when asset ID or contributor is on the copyright blocklist."""
    keys = get_stock_blocklist_keys()
    for candidate in (source_key, asset_id, contributor):
        if candidate and candidate in keys:
            return True
    if contributor:
        lowered = contributor.lower()
        if lowered in keys or f"contributor:{lowered}" in keys:
            return True
    return False


def source_asset_was_used(source_key: str, content_hash: Optional[str] = None) -> bool:
    """Checks persistent source history, which survives video deletion and restarts."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM source_assets WHERE source_key = ? OR (? IS NOT NULL AND content_hash = ?) LIMIT 1",
            (source_key, content_hash, content_hash),
        ).fetchone()
    return row is not None


def record_source_asset(
    source_key: str, source_url: str = "", content_hash: str = "", source_name: str = ""
) -> None:
    """Records a selected source once; conflicts preserve the original historical record."""
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO source_assets (source_key, source_url, content_hash, source_name) VALUES (?, ?, ?, ?)",
            (source_key, source_url, content_hash, source_name),
        )
        conn.commit()


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
    phone_type: str = "physical",
) -> int:
    """Inserts or updates a managed YouTube channel with anti-detect profile."""
    profile_id = profile_id or handle.lstrip("@")
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
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
            """,
            (
                channel_url,
                handle,
                channel_name,
                niche,
                proxy_url,
                profile_id,
                status,
                health_score,
                resting_until,
                config_json,
                recovery_email,
                phone_number,
                phone_type,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_managed_channel(identifier: str) -> Optional[Dict[str, Any]]:
    """Retrieves a managed channel by URL, handle, or ID."""
    with _conn() as conn:
        cursor = conn.cursor()
        if str(identifier).isdigit():
            cursor.execute("SELECT * FROM managed_channels WHERE id = ?", (int(identifier),))
        else:
            cursor.execute(
                "SELECT * FROM managed_channels WHERE channel_url = ? OR handle = ?",
                (identifier, identifier),
            )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_managed_channels() -> List[Dict[str, Any]]:
    """Returns all registered managed channels with health metrics."""
    with _conn() as conn:
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
    increment_cycles: bool = False,
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

    with _conn() as conn:
        cursor = conn.cursor()
        sql = f"UPDATE managed_channels SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, tuple(params))
        conn.commit()


def save_generated_script(
    script_text: str,
    title: str = "",
    keyword: str = "",
    channel_slug: str = "default",
    niche_id: str = "",
    video_id: Optional[int] = None,
    status: str = "approved",
    similarity_score: float = 0.0,
) -> int:
    """
    Bölüm 8.1 / Madde 120: Üretilen veya onaylanan senaryoyu SQLite tablosuna kaydeder.
    """
    text_clean = (script_text or "").strip()
    if not text_clean:
        return 0
    shash = hashlib.sha256(text_clean.lower().encode("utf-8")).hexdigest()
    words = len(text_clean.split())
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO generated_scripts (
                channel_slug, title, keyword, script_text, script_hash,
                niche_id, word_count, similarity_score, status, video_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(script_hash) DO UPDATE SET
                title=excluded.title,
                keyword=excluded.keyword,
                channel_slug=excluded.channel_slug,
                similarity_score=excluded.similarity_score,
                status=excluded.status
            """,
            (
                channel_slug or "default",
                title or "",
                keyword or "",
                text_clean,
                shash,
                niche_id or "",
                words,
                float(similarity_score or 0.0),
                status or "approved",
                video_id,
            ),
        )
        conn.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        cursor.execute("SELECT id FROM generated_scripts WHERE script_hash = ?", (shash,))
        row = cursor.fetchone()
        return row["id"] if row else 0


def get_recent_scripts(channel_slug: str = "default", limit: int = 50) -> List[str]:
    """
    Bölüm 8.1 / Madde 120: Belirtilen kanal için en son üretilmiş senaryoları SQLite'tan çeker.
    Kanal izolasyonu sağlar; 'default' veya '*' durumunda genel geçmişi döndürür.
    Ayrıca tamamlanmış videoların sahne anlatımlarını da geriye dönük tarar.
    """
    scripts: List[str] = []
    seen_hashes = set()
    with _conn() as conn:
        cursor = conn.cursor()
        if channel_slug in ("*", "all"):
            cursor.execute(
                """
                SELECT g.script_text, g.script_hash
                FROM generated_scripts g
                LEFT JOIN videos v ON v.id = g.video_id
                WHERE (g.status IS NULL OR g.status NOT IN ('failed', 'cancelled'))
                  AND (v.status IS NULL OR v.status != 'failed')
                ORDER BY g.created_at DESC LIMIT ?
                """,
                (limit,),
            )
        else:
            cursor.execute(
                """
                SELECT g.script_text, g.script_hash
                FROM generated_scripts g
                LEFT JOIN videos v ON v.id = g.video_id
                WHERE g.channel_slug = ?
                  AND (g.status IS NULL OR g.status NOT IN ('failed', 'cancelled'))
                  AND (v.status IS NULL OR v.status != 'failed')
                ORDER BY g.created_at DESC LIMIT ?
                """,
                (channel_slug or "default", limit),
            )
        for row in cursor.fetchall():
            st = str(row["script_text"] or "").strip()
            sh = str(row["script_hash"] or "")
            if st and sh not in seen_hashes:
                seen_hashes.add(sh)
                scripts.append(st)

        if len(scripts) < limit:
            rem = limit - len(scripts)
            if channel_slug in ("*", "all"):
                cursor.execute(
                    """
                    SELECT v.id, GROUP_CONCAT(s.narration, ' ') as full_text
                    FROM videos v
                    JOIN scenes s ON s.video_id = v.id
                    WHERE v.status = 'completed'
                    GROUP BY v.id
                    ORDER BY v.created_at DESC
                    LIMIT ?
                    """,
                    (rem,),
                )
            else:
                cursor.execute(
                    """
                    SELECT v.id, GROUP_CONCAT(s.narration, ' ') as full_text
                    FROM videos v
                    JOIN scenes s ON s.video_id = v.id
                    WHERE v.channel_slug = ? AND v.status = 'completed'
                    GROUP BY v.id
                    ORDER BY v.created_at DESC
                    LIMIT ?
                    """,
                    (channel_slug or "default", rem),
                )
            for row in cursor.fetchall():
                st = str(row["full_text"] or "").strip()
                if st:
                    sh = hashlib.sha256(st.lower().encode("utf-8")).hexdigest()
                    if sh not in seen_hashes:
                        seen_hashes.add(sh)
                        scripts.append(st)

    return scripts[:limit]


def get_script_history_detailed(
    channel_slug: str = "default", limit: int = 50
) -> List[Dict[str, Any]]:
    """Detaylı senaryo denetim günlüğü."""
    records = []
    with _conn() as conn:
        cursor = conn.cursor()
        if channel_slug in ("*", "all"):
            cursor.execute(
                "SELECT * FROM generated_scripts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        else:
            cursor.execute(
                "SELECT * FROM generated_scripts WHERE channel_slug = ? ORDER BY created_at DESC LIMIT ?",
                (channel_slug or "default", limit),
            )
        for row in cursor.fetchall():
            records.append(dict(row))
    return records
