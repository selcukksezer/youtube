"""
Test Suite for Bölüm 15: CLI Komutları, REST API ve SSE/WebSocket Sözleşmeleri.
Verifies cli.py parsing/dry-run execution and /api/v1/jobs REST/SSE endpoints.
"""
import subprocess
import sys
import unittest
from fastapi.testclient import TestClient

from server import app
from cli import build_parser, run_cli


class TestChapter15CliAndRest(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    # ─── 15.1 CLI Referansı Testleri ───
    def test_cli_parser_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["--topic", "Yapay Zeka ile Pasif Gelir"])
        self.assertEqual(args.topic, "Yapay Zeka ile Pasif Gelir")
        self.assertEqual(args.niche, "4_ai_money_tech")
        self.assertEqual(args.duration, 45)
        self.assertEqual(args.engine, "ffmpeg_native")
        self.assertEqual(args.hwaccel, "auto")
        self.assertEqual(args.voice, "tr-TR-AhmetNeural")
        self.assertEqual(args.subtitle_style, "capcut_yellow")
        self.assertTrue(args.anti_detect)
        self.assertFalse(args.dry_run)

    def test_cli_dry_run_execution(self):
        parser = build_parser()
        args = parser.parse_args([
            "--topic", "Göz Teması ve Beden Dili Psikolojisi",
            "--niche", "6_psychology_tricks",
            "--dry-run",
        ])
        exit_code = run_cli(args)
        self.assertEqual(exit_code, 0)

    # ─── 15.2 FastAPI REST API & SSE Testleri ───
    def test_create_job_v1_accepted(self):
        from unittest.mock import patch
        import sys
        mod = sys.modules.get("routers.jobs_v1_router")
        with patch.object(mod, "process_video_task", return_value=None):
            payload = {
                "topic": "Antik Roma'nın En Çılgın 3 İmparatoru",
                "niche_id": "3_bizarre_history",
                "duration_sec": 45,
                "engine": "ffmpeg_native",
                "hwaccel": "auto",
                "subtitle_style": "history_sepia",
                "voice": "tr-TR-AhmetNeural",
                "auto_publish": False,
            }
            resp = self.client.post("/api/v1/jobs/create", json=payload)
            self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertIn("job_id", data)
        self.assertEqual(data["status"], "QUEUED")
        self.assertEqual(data["progress_pct"], 0)
        self.assertIn(f"/api/v1/jobs/{data['job_id']}/events", data["sse_url"])

        # Query status
        job_id = data["job_id"]
        status_resp = self.client.get(f"/api/v1/jobs/{job_id}/status")
        self.assertEqual(status_resp.status_code, 200)
        sdata = status_resp.json()
        self.assertEqual(sdata["job_id"], job_id)
        self.assertIn(sdata["status"], ["QUEUED", "RENDERING", "COMPLETED"])

        # Cancel job
        cancel_resp = self.client.post(f"/api/v1/jobs/{job_id}/cancel")
        self.assertEqual(cancel_resp.status_code, 200)
        cdata = cancel_resp.json()
        self.assertEqual(cdata["status"], "CANCELLED")

    def test_nonexistent_job_status_404(self):
        resp = self.client.get("/api/v1/jobs/non_existent_uuid_12345/status")
        self.assertEqual(resp.status_code, 404)

    def test_nonexistent_job_cancel_404(self):
        resp = self.client.post("/api/v1/jobs/non_existent_uuid_12345/cancel")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
