"""
visuals — unified, license-aware visual sourcing for Shorts scenes.

Layers:
  license.py         License model + commercial-safety rules + attribution text
  providers.py       Search adapters (Pexels, Pixabay, Coverr, Wikimedia, NASA, Openverse, Archive.org)
  registry.py        Provider availability, per-niche preference, cache, dedupe, scoring
  query_builder.py   Turkish narration -> English SHOT queries + fallback ladder
  palettes.py        Niche palette + motion profile for procedural graphics
  motion_graphics.py Kinetic typography / gradient clip generator (procedural tier)
  fetch.py           Orchestrator: candidates -> download -> normalize 9:16 -> manifest
  ai_video/          Free AI T2V providers + AI/stock/procedural mixer
"""
from .fetch import fetch_open_visual, write_job_credits, reset_job_manifest, get_job_manifest  # noqa: F401
from .license import License, LicenseInfo, is_commercial_safe, attribution_line  # noqa: F401
from .query_builder import build_shot_queries, validate_query_list  # noqa: F401
from .palettes import family_for_niche, palette_for, preferred_sources  # noqa: F401
