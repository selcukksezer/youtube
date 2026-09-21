# Production Deploy Runbook

> Docker + manual operator workflow. Automatic YouTube Studio upload remains **out of scope**.

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Docker 24+ | `docker compose` v2 |
| FFmpeg | Included in image |
| `.env` | From vault unseal or `.env.example` copy |

## 1. Secrets & environment

```bash
# Unseal encrypted env (if using vault)
python scripts/env_vault.py unseal

# Or copy template and fill keys manually
cp .env.example .env
```

Minimum keys for render:

- `GEMINI_API_KEY` — scenario generation
- `GEMINI_MODEL=gemini-flash-lite-latest` (or current free-tier model)
- `RENDER_RESOLUTION_MODE=1080p`
- `RENDER_SAFE_MODE=false`

Optional:

- `PEXELS_API_KEY`, `PIXABAY_API_KEY` — stock fallback
- `DB_BACKUP_PASSPHRASE` + `ENABLE_DB_BACKUP=true` — encrypted SQLite backup

## 2. Build & run (Docker)

```bash
docker compose build
docker compose up -d
```

Health check: `curl -f http://127.0.0.1:8000/` (or `${APP_PORT}`).

Volumes mounted: `output/`, `data/`, `assets/`, `bgm/`, `proofs/`.

## 3. Local / bare-metal (dev)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run_ui.sh
# or: uvicorn server:app --host 0.0.0.0 --port 8000
```

## 4. Post-deploy smoke

1. Open UI → generate script for one topic (crypto / stoic / astro).
2. Run render → confirm MP4 in `output/<channel>/`.
3. Check SEO operator pack: `GET /api/seo/operator-pack?keyword=Test`
4. Check growth pack: `GET /api/growth/operator-pack?topic=Test`

## 5. Operator upload (manual)

1. Download rendered MP4 + thumbnail from `output/`.
2. Paste metadata from SEO operator pack into YouTube Studio.
3. Apply engagement checklist (pin comment, heart first comments).
4. Do **not** enable prod Playwright auto-upload unless explicitly approved (Excluded scope).

## 6. Backup & maintenance

- Encrypted DB backup: set `ENABLE_DB_BACKUP=true` and passphrase.
- Old renders: `purge_old_videos` (30-day) runs in render worker when configured.
- `data/quota_usage.json` is runtime-only — not committed (see `.gitignore`).

## 7. CI

GitHub Actions runs `python -m unittest discover -s tests -p 'test_*.py'` on push/PR to `main`.

## Troubleshooting

| Symptom | Action |
|---------|--------|
| 429 Gemini | Check quota panel; circuit breaker falls back to procedural |
| FFmpeg missing | Rebuild Docker image or `brew install ffmpeg` |
| Port in use | `run_ui.sh` kills stale uvicorn; set `APP_PORT` |
| Empty BGM | `AUTO_FETCH_ROYALTY_FREE_BGM=true` on first render |
