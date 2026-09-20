#!/usr/bin/env python3
"""Encrypt/decrypt .env for safe cross-machine transfer via git.

Usage:
  python scripts/env_vault.py seal              # encrypt .env -> .env.vault
  python scripts/env_vault.py unseal            # decrypt .env.vault -> .env
  python scripts/env_vault.py seal -p PASS      # non-interactive (avoid shell history)

Passphrase is NEVER stored in the repo. Remember it or use a password manager.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
VAULT_FILE = ROOT / ".env.vault"
MAGIC = b"SVCENV1\x00"
SALT_SIZE = 16
PBKDF2_ITER = 480_000


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, PBKDF2_ITER, dklen=32)


def _xor_stream(data: bytes, key: bytes) -> bytes:
    """Simple stream cipher — key stretched via SHA-256 chain."""
    out = bytearray(len(data))
    block = key
    pos = 0
    while pos < len(data):
        block = hashlib.sha256(block).digest()
        chunk = min(len(block), len(data) - pos)
        for i in range(chunk):
            out[pos + i] = data[pos + i] ^ block[i]
        pos += chunk
    return bytes(out)


def seal(passphrase: str) -> None:
    if not ENV_FILE.is_file():
        print(f"ERROR: {ENV_FILE} not found. Create .env first.", file=sys.stderr)
        sys.exit(1)
    if not passphrase:
        print("ERROR: empty passphrase.", file=sys.stderr)
        sys.exit(1)

    plaintext = ENV_FILE.read_bytes()
    salt = os.urandom(SALT_SIZE)
    key = _derive_key(passphrase, salt)
    ciphertext = _xor_stream(plaintext, key)
    blob = MAGIC + salt + ciphertext
    encoded = base64.b64encode(blob)
    VAULT_FILE.write_bytes(encoded)
    print(f"Sealed {ENV_FILE.name} -> {VAULT_FILE.name} ({len(plaintext)} bytes plaintext)")


def unseal(passphrase: str, force: bool = False) -> None:
    if not VAULT_FILE.is_file():
        print(f"ERROR: {VAULT_FILE} not found. Run seal on source machine first.", file=sys.stderr)
        sys.exit(1)
    if ENV_FILE.is_file() and not force:
        print(f"ERROR: {ENV_FILE} already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)
    if not passphrase:
        print("ERROR: empty passphrase.", file=sys.stderr)
        sys.exit(1)

    try:
        blob = base64.b64decode(VAULT_FILE.read_bytes())
    except Exception as exc:
        print(f"ERROR: invalid vault file: {exc}", file=sys.stderr)
        sys.exit(1)

    if not blob.startswith(MAGIC):
        print("ERROR: vault format mismatch (wrong file or passphrase needed).", file=sys.stderr)
        sys.exit(1)

    salt = blob[len(MAGIC) : len(MAGIC) + SALT_SIZE]
    ciphertext = blob[len(MAGIC) + SALT_SIZE :]
    key = _derive_key(passphrase, salt)
    plaintext = _xor_stream(ciphertext, key)

    if b"=" not in plaintext and b"\n" not in plaintext[:200]:
        print("ERROR: wrong passphrase or corrupted vault.", file=sys.stderr)
        sys.exit(1)

    ENV_FILE.write_bytes(plaintext)
    print(f"Unsealed {VAULT_FILE.name} -> {ENV_FILE.name}")


def _read_passphrase(args: argparse.Namespace, prompt: str) -> str:
    if args.passphrase:
        return args.passphrase
    env_pass = os.environ.get("ENV_VAULT_PASSPHRASE", "")
    if env_pass:
        return env_pass
    p1 = getpass.getpass(prompt)
    p2 = getpass.getpass("Confirm passphrase: ")
    if p1 != p2:
        print("ERROR: passphrases do not match.", file=sys.stderr)
        sys.exit(1)
    return p1


def main() -> None:
    parser = argparse.ArgumentParser(description="Seal/unseal .env for secure git transfer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    seal_p = sub.add_parser("seal", help="Encrypt .env -> .env.vault")
    seal_p.add_argument("-p", "--passphrase", help="Passphrase (prefer interactive or ENV_VAULT_PASSPHRASE)")

    unseal_p = sub.add_parser("unseal", help="Decrypt .env.vault -> .env")
    unseal_p.add_argument("-p", "--passphrase", help="Passphrase")
    unseal_p.add_argument("--force", action="store_true", help="Overwrite existing .env")

    args = parser.parse_args()
    if args.cmd == "seal":
        pw = _read_passphrase(args, "Vault passphrase (remember this): ")
        seal(pw)
    elif args.cmd == "unseal":
        pw = _read_passphrase(args, "Vault passphrase: ")
        unseal(pw, force=args.force)


if __name__ == "__main__":
    main()
