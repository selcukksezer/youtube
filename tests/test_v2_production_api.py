import json
import uuid

import database
import server


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
