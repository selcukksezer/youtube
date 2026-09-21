# ROADMAP_AUDIT — Sprint 2 Recovery Note

> **Incident:** `git checkout HEAD -- ROADMAP_AUDIT.md` during Sprint 2 accidentally reverted the 2026-09-21 rewritten audit (217 Done baseline) to the older 2026-09-20 format.
> **Code + tests remain valid.** Restore full per-item table from parent sprint transcript or re-run audit generator.

## Sprint 2 Executive Summary (2026-09-21)

| Durum | Sayı | Not |
|-------|------|-----|
| ✅ Done (post Sprint 1+2+3) | **~330** | +56 Batch 3 (274 baseline) |
| 🟡 Partial | **~59** | B6 SEO, B2 enrichment, B8 advisory kalan |
| ❌ Missing | **0** | #422 Docker, #439 backup implemented |
| 🔜 Deferred | **~24** | +9 B5 growth (#311–322, #324 D-ID) |

## Sprint 2 — Partial → Done (57 targeted)

### Root fix
`DirectorPlan.to_legacy_plan()` dropped `hybrid_render_overlay` + `retention_metadata` → B5 overlays never reached `video_composer`. Fixed in `director/schema.py`, `director/compiler.py`.

### Batch A — B5 hybrid overlay (43 niches)
#289–309, #316–318, #325–328, #331–335, #337–344 + mapped overlays

Evidence: `hybrid_niches.get_hybrid_render_overlay_spec` → `apply_hybrid_render_overlay` + `test_batch5_director_hybrid_preservation.py`

### Batch B — B4 retention/subtitle (12)
#207, #213, #214, #217, #225, #229, #230, #234, #237, #239, #247, #265

### Batch C — B5 growth hooks (4)
#310 A/B subtitle, #323 60fps, #334 single-sentence hook, #345 perfect loop

### Batch D — B7 infra (2)
#422 `Dockerfile` + `docker-compose.yml` | #439 `database.encrypted_db_backup`

### Deferred (honest)
#311–322 growth/SEO Studio-only | #324 D-ID API key

## Tests added/passing
- `tests/test_batch4_completion_sprint_wiring.py`
- `tests/test_batch5_director_hybrid_preservation.py`

## Batch 3 Completion (2026-09-21) — +56 Partial→Done

B3 audio, B4 retention visual, B5 17 hybrid overlay, B7 ops (#413,#432,#448,#450), RENDER_SAFE default path.

**Test:** `tests/test_batch3_completion_sprint_wiring.py`

## Batch 4 Completion (2026-09-21) — +56 Partial→Done

386 Done / 3 Partial / 24 Deferred. Tests: `test_completion_sprint_batch4_wiring.py`.

## Remaining Partial (3 in-scope)
- #472–474 appeal video filming (script generated; camera/screen record manual)
