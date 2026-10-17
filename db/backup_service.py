"""
Encrypted SQLite Online Backup & Restore Service (Item 439).
"""
import hashlib
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Optional
import database


_BACKUP_MAGIC = b"YTDBKP1\x00"


def _xor_stream(payload: bytes, secret: str, salt: bytes) -> bytes:
    """Symmetric PBKDF2-derived SHA-256 keystream (same for encrypt/decrypt)."""
    key = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, 480_000, dklen=32)
    block = key
    out = bytearray(len(payload))
    pos = 0
    while pos < len(payload):
        block = hashlib.sha256(block).digest()
        take = min(len(block), len(payload) - pos)
        for i in range(take):
            out[pos + i] = payload[pos + i] ^ block[i]
        pos += take
    return bytes(out)


def encrypted_db_backup(
    dest_dir: Optional[str] = None,
    passphrase: Optional[str] = None,
    keep: int = 7,
) -> Optional[str]:
    """
    Item 439: Encrypted SQLite backup (PBKDF2 + XOR stream, env_vault compatible).
    Uses DB_BACKUP_PASSPHRASE or ENV_VAULT_PASSPHRASE from environment when set.
    """
    db_path = database.DB_PATH
    backup_dir = database.BACKUP_DIR
    if not os.path.isfile(db_path):
        return None
    out_dir = dest_dir or backup_dir
    os.makedirs(out_dir, exist_ok=True)
    secret = (
        passphrase
        or os.getenv("DB_BACKUP_PASSPHRASE")
        or os.getenv("ENV_VAULT_PASSPHRASE")
        or "youtubeoto-local-backup"
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    plain_copy = os.path.join(out_dir, f"shorts_{stamp}.db")
    enc_path = os.path.join(out_dir, f"shorts_{stamp}.db.enc")
    # WAL mode: a raw file copy can miss pages still in shorts.db-wal.
    # sqlite3's online backup API produces a consistent snapshot.
    src_conn = sqlite3.connect(db_path, timeout=15.0)
    try:
        dst_conn = sqlite3.connect(plain_copy)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()
    salt = os.urandom(16)
    with open(plain_copy, "rb") as src:
        payload = src.read()
    encrypted = _xor_stream(payload, secret, salt)
    with open(enc_path, "wb") as out:
        out.write(_BACKUP_MAGIC)
        out.write(salt)
        out.write(encrypted)
    try:
        os.remove(plain_copy)
    except OSError:
        pass
    backups = sorted(
        [f for f in os.listdir(out_dir) if f.endswith(".db.enc")],
        reverse=True,
    )
    for old in backups[keep:]:
        try:
            os.remove(os.path.join(out_dir, old))
        except OSError:
            pass
    print(f"[DB Backup] Encrypted backup written: {enc_path}")
    return enc_path


def decrypt_db_backup(enc_path: str, out_path: str, passphrase: Optional[str] = None) -> str:
    """
    Restore counterpart of encrypted_db_backup(): writes a plain SQLite file to out_path.
    Raises ValueError on bad magic / wrong passphrase (result is not a SQLite file).
    """
    secret = (
        passphrase
        or os.getenv("DB_BACKUP_PASSPHRASE")
        or os.getenv("ENV_VAULT_PASSPHRASE")
        or "youtubeoto-local-backup"
    )
    with open(enc_path, "rb") as fh:
        blob = fh.read()
    if not blob.startswith(_BACKUP_MAGIC):
        raise ValueError("Not a youtubeoto encrypted DB backup (bad magic header)")
    salt = blob[len(_BACKUP_MAGIC) : len(_BACKUP_MAGIC) + 16]
    plain = _xor_stream(blob[len(_BACKUP_MAGIC) + 16 :], secret, salt)
    if not plain.startswith(b"SQLite format 3\x00"):
        raise ValueError("Decryption produced a non-SQLite file — wrong passphrase?")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as out:
        out.write(plain)
    return out_path


def maybe_schedule_encrypted_db_backup() -> Optional[str]:
    """Run encrypted_db_backup when ENABLE_DB_BACKUP=true (Item 439)."""
    if os.getenv("ENABLE_DB_BACKUP", "false").lower() not in ("1", "true", "yes"):
        return None
    backup_dir = database.BACKUP_DIR
    interval_h = float(os.getenv("DB_BACKUP_INTERVAL_HOURS", "24") or "24")
    marker = os.path.join(backup_dir, ".last_backup_ts")
    os.makedirs(backup_dir, exist_ok=True)
    now = time.time()
    last = 0.0
    if os.path.isfile(marker):
        try:
            with open(marker, encoding="utf-8") as fh:
                last = float(fh.read().strip() or "0")
        except Exception:
            last = 0.0
    if now - last < interval_h * 3600:
        return None
    path = encrypted_db_backup()
    if path:
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write(str(now))
    return path
