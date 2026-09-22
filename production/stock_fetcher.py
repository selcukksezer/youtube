"""Async, license-aware stock search facade.

Provider adapters are synchronous because some public archives use requests;
this facade runs them concurrently without changing their tested behavior.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Dict, List

from visuals.providers import Candidate
from visuals.registry import ordered_providers, search_provider, score_candidate
from visuals.query_builder import build_shot_queries


class AsyncStockFetcher:
    def __init__(self, niche_id: str = "") -> None:
        self.niche_id = niche_id

    async def search(self, *, narration: str = "", scene_description: str = "", queries: List[str] | None = None, limit: int = 12) -> List[Candidate]:
        shot_queries = list(queries or []) or build_shot_queries(
            narration=narration,
            scene_description=scene_description,
            niche_id=self.niche_id,
        )
        specs = ordered_providers(self.niche_id)
        jobs = [
            asyncio.to_thread(search_provider, spec, query, 8)
            for query in shot_queries[:5]
            for spec in specs
        ]
        groups = await asyncio.gather(*jobs, return_exceptions=True)
        ranked: Dict[str, tuple[float, Candidate]] = {}
        for group in groups:
            if isinstance(group, Exception):
                continue
            for candidate in group:
                score = max(
                    score_candidate(candidate, query, narration=narration, target_duration=5.0)
                    for query in shot_queries[:5]
                )
                if score <= 0:
                    continue
                old = ranked.get(candidate.uid)
                if old is None or score > old[0]:
                    ranked[candidate.uid] = (score, candidate)
        return [candidate for _, candidate in sorted(ranked.values(), key=lambda row: row[0], reverse=True)[:limit]]

    async def search_dicts(self, **kwargs) -> List[dict]:
        return [candidate.to_dict() for candidate in await self.search(**kwargs)]
