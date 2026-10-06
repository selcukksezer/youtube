"""
Tests for 'Tüm Videoları MiniMax-H3 İle Üret' and stock video clearing feature.
Covers:
- /api/project/clear_stock_cache endpoint functionality
- render_worker override of previous stock clips when visual_mode is minimax_h3
"""
import os
import tempfile
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

import importlib
_vr_module = importlib.import_module("routers.video_router")
clear_stock_cache = getattr(_vr_module, "clear_stock_cache", None)
import config


def test_clear_stock_cache_endpoint():
    with tempfile.TemporaryDirectory() as tmp_base:
        orig_base = config.BASE_DIR
        try:
            config.BASE_DIR = tmp_base
            assets_dir = os.path.join(tmp_base, "assets", "test_project")
            os.makedirs(assets_dir, exist_ok=True)

            stock_file = os.path.join(assets_dir, "s001_pexels_nature.mp4")
            with open(stock_file, "wb") as f:
                f.write(b"video data")

            keep_file = os.path.join(assets_dir, "audio.mp3")
            with open(keep_file, "wb") as f:
                f.write(b"audio data")

            mock_req = MagicMock()
            mock_req.json = AsyncMock(return_value={"topic": "test_project"})

            res = asyncio.run(clear_stock_cache(mock_req))
            assert res["status"] == "ok"
            assert res["deleted_count"] == 1
            assert not os.path.exists(stock_file)
            assert os.path.exists(keep_file)
        finally:
            config.BASE_DIR = orig_base


def test_render_worker_minimax_overrides_stock():
    """Verify that when visual_mode is minimax_h3, stock local candidates are suppressed."""
    from server_core.render_worker import _fetch_single_scene_visual

    scene = {
        "text": "Antik Roma sokakları",
        "duration": 4.0,
        "visual_mode": "minimax_h3",
        "selected_video": {
            "path": "c:/tmp/s001_pexels_ancient_rome.mp4",
            "source": "Pexels"
        }
    }

    with patch("os.path.exists", return_value=True), \
         patch("visuals.ai_video.providers.minimax_h3.generate_local_h3_clip", return_value="/out/s001_minimax_h3.mp4") as mock_h3:
        
        path = _fetch_single_scene_visual(
            i=0,
            scene=scene,
            plan={"visual_mode": "minimax_h3"},
            proj="/tmp/proj",
            total_s=1,
            req=MagicMock(visual_mode="minimax_h3"),
        )
        assert mock_h3.called
        assert path[2] == "/out/s001_minimax_h3.mp4"
