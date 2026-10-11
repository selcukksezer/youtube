import json
import uuid

import database
import server
import v2_api.router as v2_router
from api_models import VideoRenderRequest
from fastapi.testclient import TestClient
from server_core import state


def test_v2_routes_are_published():
    paths = server.app.openapi()["paths"]
    assert "/api/v2/projects" in paths
    assert "/api/v2/projects/{project_id}/render" in paths
    assert "/api/v2/render-jobs/{job_id}/events" in paths


def test_project_and_render_job_persistence():
    project_id = f"test_{uuid.uuid4().hex}"
    job_id = f"job_{uuid.uuid4().hex}"
    try:
        project = database.create_project(project_id, "V2 Test")
        assert project["status"] == "draft"
        database.update_project(project_id, status="ready_to_render", plan_json=json.dumps({"scenes": []}))
        assert database.get_project(project_id)["status"] == "ready_to_render"
        job = database.create_render_job(job_id, project_id)
        assert job["status"] == "queued"
        database.update_render_job(job_id, status="completed", percent=100, output_url="/output/test.mp4")
        saved = database.get_render_job(job_id)
        assert saved["status"] == "completed"
        assert saved["percent"] == 100
    finally:
        with database.get_connection() as conn:
            conn.execute("DELETE FROM render_jobs WHERE id = ?", (job_id,))
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()


def test_render_job_event_history_replays_after_last_event_id():
    project_id = f"test_{uuid.uuid4().hex}"
    job_id = f"job_{uuid.uuid4().hex}"
    try:
            database.create_project(project_id, "V2 Event History Test")
            database.create_render_job(job_id, project_id)
            queued_event = database.list_render_job_events(job_id)[0]
            log_event_id = database.append_render_job_event(
                job_id, "log", "Render adımı tamamlandı"
            )
            database.update_render_job(job_id, status="completed", percent=100)

            response = TestClient(server.app).get(
                f"/api/v2/render-jobs/{job_id}/events",
                headers={"Last-Event-ID": str(queued_event["id"])},
            )

            assert response.status_code == 200
            assert f"id: {log_event_id}\nevent: render.event" in response.text
            assert "Render adımı tamamlandı" in response.text
            assert '"status": "completed"' in response.text
            assert queued_event["event_type"] == "status"
            assert queued_event["payload"] == {"status": "queued"}
    finally:
            with database.get_connection() as conn:
                conn.execute("DELETE FROM render_jobs WHERE id = ?", (job_id,))
                conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                conn.commit()


def test_render_worker_events_are_persisted_for_active_job(monkeypatch):
    project_id = f"test_{uuid.uuid4().hex}"
    job_id = f"job_{uuid.uuid4().hex}"
    try:
        database.create_project(project_id, "V2 Worker Event Test")
        database.create_render_job(job_id, project_id)
        monkeypatch.setattr(state, "active_render_job_id", job_id)
        monkeypatch.setitem(state.current_render_state, "logs", [])

        state.broadcast_event("log", "Varlıklar hazırlandı")

        events = database.list_render_job_events(job_id)
        assert events[-1]["event_type"] == "log"
        assert events[-1]["payload"] == "Varlıklar hazırlandı"
    finally:
        with database.get_connection() as conn:
                conn.execute("DELETE FROM render_jobs WHERE id = ?", (job_id,))
                conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                conn.commit()


def test_startup_cleanup_fails_stale_render_jobs_and_restores_projects():
    project_id = f"test_{uuid.uuid4().hex}"
    stale_job_id = f"job_{uuid.uuid4().hex}"
    completed_job_id = f"job_{uuid.uuid4().hex}"
    try:
        database.create_project(project_id, "V2 Restart Recovery Test")
        database.update_project(project_id, status="rendering")
        database.create_render_job(stale_job_id, project_id)
        database.update_render_job(stale_job_id, status="cancelling", step="İptal bekleniyor")
        database.create_render_job(completed_job_id, project_id)
        database.update_render_job(completed_job_id, status="completed", percent=100)

        database.cleanup_stale_tasks()

        stale_job = database.get_render_job(stale_job_id)
        assert stale_job is not None
        assert stale_job["status"] == "failed"
        assert stale_job["step"] == "Başarısız"
        assert stale_job["error_message"] == "Sunucu yeniden başlatıldı; render işi tamamlanamadı."
        stale_events = database.list_render_job_events(stale_job_id)
        assert stale_events[-1]["payload"]["error_message"] == stale_job["error_message"]
        assert stale_events[-1]["payload"]["status"] == "failed"
        assert database.get_render_job(completed_job_id)["status"] == "completed"
        assert database.get_project(project_id)["status"] == "ready_to_render"
    finally:
        with database.get_connection() as conn:
            conn.execute("DELETE FROM render_jobs WHERE id IN (?, ?)", (stale_job_id, completed_job_id))
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()


def test_queued_render_cancellation_is_honored_before_worker_starts(monkeypatch):
    project_id = f"test_{uuid.uuid4().hex}"
    job_id = f"job_{uuid.uuid4().hex}"
    try:
        database.create_project(project_id, "V2 Queued Cancellation Test")
        database.update_project(project_id, status="rendering", plan_json=json.dumps({"scenes": []}))
        database.create_render_job(job_id, project_id)
        monkeypatch.setattr(state, "is_rendering_active", True)
        monkeypatch.setattr(state, "active_render_job_id", None)
        monkeypatch.setitem(state.current_render_state, "cancel_requested", False)
        worker_calls = []

        def record_worker(req, *, reset_cancel_request=True):
            worker_calls.append((req, reset_cancel_request))

        monkeypatch.setattr(
            v2_router,
            "process_video_task",
            record_worker,
        )

        v2_router.cancel_job(job_id)
        v2_router._run_job(
            job_id,
            project_id,
            VideoRenderRequest(keyword="Test", plan={"scenes": []}),
        )

        assert database.get_render_job(job_id)["status"] == "cancelled"
        assert database.get_project(project_id)["status"] == "ready_to_render"
        assert worker_calls == []
        assert state.is_rendering_active is False
        assert state.active_render_job_id is None
    finally:
        with database.get_connection() as conn:
            conn.execute("DELETE FROM render_jobs WHERE id = ?", (job_id,))
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()


def test_active_render_cancellation_is_persisted_as_cancelled(monkeypatch):
    project_id = f"test_{uuid.uuid4().hex}"
    job_id = f"job_{uuid.uuid4().hex}"
    try:
        database.create_project(project_id, "V2 Active Cancellation Test")
        database.update_project(project_id, status="rendering", plan_json=json.dumps({"scenes": []}))
        database.create_render_job(job_id, project_id)
        monkeypatch.setattr(state, "is_rendering_active", True)
        monkeypatch.setattr(state, "active_render_job_id", None)
        monkeypatch.setitem(state.current_render_state, "cancel_requested", False)
        monkeypatch.setitem(state.current_render_state, "error", None)

        def cancel_during_render(req, *, reset_cancel_request):
            assert req.keyword == "Test"
            assert reset_cancel_request is False
            v2_router.cancel_job(job_id)
            state.broadcast_event("progress", {"percent": 5, "step": "İptal bekleniyor"})
            assert database.get_render_job(job_id)["status"] == "cancelling"
            state.broadcast_event("error", "⛔ Video üretimi kullanıcı tarafından iptal edildi.")

        monkeypatch.setattr(v2_router, "process_video_task", cancel_during_render)
        v2_router._run_job(
            job_id,
            project_id,
            VideoRenderRequest(keyword="Test", plan={"scenes": []}),
        )

        saved_job = database.get_render_job(job_id)
        assert saved_job["status"] == "cancelled"
        assert saved_job["step"] == "İptal edildi"
        assert database.get_project(project_id)["status"] == "ready_to_render"
    finally:
        with database.get_connection() as conn:
            conn.execute("DELETE FROM render_jobs WHERE id = ?", (job_id,))
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
