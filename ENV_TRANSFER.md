# Secure API Key Transfer (Cross-Machine)

Plaintext `.env` is **never** committed. Use the encrypted vault instead.

## Machine A (this PC) — before push

```powershell
# 1. Ensure .env has your real keys
# 2. Seal with a passphrase YOU remember (not stored in git)
python scripts/env_vault.py seal

# 3. Verify .env is NOT staged
git status

# 4. Stage only .env.vault (encrypted blob)
git add .env.vault

# 5. Optional: scan before push
python scripts/scan_secrets.py
git push
```

Non-interactive seal (PowerShell, avoid logging passphrase):

```powershell
$env:ENV_VAULT_PASSPHRASE = "your-master-passphrase"
python scripts/env_vault.py seal
Remove-Item Env:ENV_VAULT_PASSPHRASE
```

## Machine B (tomorrow) — after clone

```powershell
git clone https://github.com/selcukksezer/youtube.git
cd youtube
python scripts/env_vault.py unseal
# enter same passphrase → .env restored

pip install -r requirements.txt
python run.py
```

## Rules

| File | Git | Notes |
|------|-----|-------|
| `.env` | **NEVER** | Real keys — local only |
| `.env.vault` | ✅ safe | Encrypted blob |
| `.env.example` | ✅ safe | Placeholders only |

## Re-seal after key changes

Any time you update keys in `.env`:

```powershell
python scripts/env_vault.py seal
git add .env.vault
git commit -m "chore: re-seal env vault"
git push
```

## Alternative: GitHub Codespaces Secrets

For cloud dev only — add repo secrets in GitHub Settings → Secrets. Not needed if you use `.env.vault`.

## Pre-push secret scan

```powershell
git add ...
python scripts/scan_secrets.py   # must exit 0 before push
git push
```
