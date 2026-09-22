import os

import kids_song_bridge
import server


def test_kids_song_routes_are_published():
    paths = server.app.openapi()["paths"]
    assert "/api/kids-song/status" in paths
    assert "/api/kids-song/start" in paths
    assert "/api/kids-song/stop" in paths


def test_missing_studio_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("KIDS_SONG_STUDIO_DIR", str(tmp_path / "yok"))
    payload = kids_song_bridge.status()
    assert payload["installed"] is False
    assert payload["running"] is False
    assert "bulunamadı" in payload["message"]


def test_studio_without_dependencies(monkeypatch, tmp_path):
    studio = tmp_path / "studio"
    studio.mkdir()
    (studio / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("KIDS_SONG_STUDIO_DIR", str(studio))
    monkeypatch.setattr(kids_song_bridge, "port_open", lambda *args, **kwargs: False)
    payload = kids_song_bridge.status()
    assert payload["installed"] is True
    assert payload["dependencies"] is False
    assert "npm install" in payload["message"]


def test_start_refuses_missing_install(monkeypatch, tmp_path):
    monkeypatch.setenv("KIDS_SONG_STUDIO_DIR", str(tmp_path / "yok"))
    payload = kids_song_bridge.start()
    assert payload["ok"] is False
    assert os.path.isdir(str(tmp_path / "yok")) is False


def test_new_bridge_routes_are_published():
    paths = server.app.openapi()["paths"]
    assert "/api/kids-song/projects" in paths
    assert "/api/kids-song/projects/{project_id}" in paths
    assert "/api/kids-song/projects/{project_id}/import" in paths
    assert "/api/kids-song/settings/transfer" in paths


def test_list_projects_offline(monkeypatch):
    monkeypatch.setattr(kids_song_bridge, "port_open", lambda *args, **kwargs: False)
    payload = kids_song_bridge.list_projects()
    assert payload["ok"] is False
    assert "kapalı" in payload["error"]
    assert payload["status_code"] == 503


def test_create_project_offline(monkeypatch):
    monkeypatch.setattr(kids_song_bridge, "port_open", lambda *args, **kwargs: False)
    payload = kids_song_bridge.create_project("Deneme Sarkisi")
    assert payload["ok"] is False
    assert "kapalı" in payload["error"]


def test_parse_project_list_envelope():
    payload = {
        "ok": True,
        "data": [
            {
                "id": "proj1",
                "name": "Uzay",
                "title": "Uzay Sarkisi",
                "slug": "uzay",
                "status": "draft",
                "clipCount": 4,
                "completedClipCount": 1,
            }
        ],
    }
    items = kids_song_bridge.parse_project_list(payload)
    assert items[0]["id"] == "proj1"
    assert items[0]["clip_count"] == 4
    assert items[0]["render_path"] == "/cocuk-sarki/proj1/render"


def test_summarize_project_phases():
    preparing = kids_song_bridge.summarize_project(
        {"id": "p1", "name": "A", "slug": "a", "status": "draft", "clips": [], "jobs": []},
        {"finals": []},
    )
    assert preparing["label"] == "hazırlanıyor"
    assert preparing["final_exists"] is False

    automation = kids_song_bridge.summarize_project(
        {
            "id": "p2",
            "name": "B",
            "slug": "b",
            "status": "automating",
            "clips": [{"status": "completed"}, {"status": "generating"}],
            "jobs": [{"state": "running"}],
        },
        {"finals": []},
    )
    assert automation["label"] == "otomasyon"
    assert automation["completed_clip_count"] == 1
    assert automation["clip_count"] == 2

    done = kids_song_bridge.summarize_project(
        {"id": "p3", "name": "C", "slug": "c", "status": "rendering", "clips": [], "jobs": []},
        {"ok": True, "data": {"finals": [{"path": "C:/projects/c/output/final.mp4", "fileName": "final.mp4"}]}},
    )
    assert done["label"] == "render bitti"
    assert done["final_exists"] is True
    assert done["final_name"] == "final.mp4"
    assert done["render_path"] == "/cocuk-sarki/p3/render"


def test_create_body_matches_kids_schema():
    body = kids_song_bridge.build_create_body("Deneme", "Uzay")
    assert body["name"] == "Deneme"
    assert body["title"] == "Deneme"
    assert body["topic"] == "Uzay"
    assert body["templateType"] == "kids_song"
    assert body["genre"] == "Cocuk sarkisi"
    assert "lyrics" not in body


def test_create_project_uses_upload_lyrics(monkeypatch):
    calls = []

    def fake_request(method, path, body=None, form=None, timeout=12.0):
        calls.append((method, path, body, form))
        if path == "/api/projects":
            return {"id": "abc", "slug": "deneme", "name": "Deneme", "title": "Deneme", "topic": "Uzay"}
        if path.endswith("/song/upload-lyrics"):
            return {"formattedLyrics": form["lyrics"], "lyricsSource": "manual"}
        raise AssertionError(path)

    monkeypatch.setattr(kids_song_bridge, "port_open", lambda *args, **kwargs: True)
    monkeypatch.setattr(kids_song_bridge, "_studio_request", fake_request)
    payload = kids_song_bridge.create_project("Deneme", "Uzay", "la la la la la")
    assert payload["ok"] is True
    assert payload["project"]["render_path"] == "/cocuk-sarki/abc/render"
    assert payload["project"]["lyrics_saved"] is True
    assert calls[0][0] == "POST"
    assert calls[0][1] == "/api/projects"
    assert calls[1][1] == "/api/projects/abc/song/upload-lyrics"
    assert calls[1][3]["lyrics"] == "la la la la la"


def test_transfer_writes_blank_env_without_echoing_secret(monkeypatch, tmp_path, capsys):
    studio = tmp_path / "studio"
    studio.mkdir()
    (studio / "package.json").write_text("{}", encoding="utf-8")
    env_file = studio / ".env"
    env_file.write_text('OPENAI_API_KEY=""\nSUNO_API_KEY="sk-..."\n', encoding="utf-8")
    monkeypatch.setenv("KIDS_SONG_STUDIO_DIR", str(studio))
    monkeypatch.setattr(kids_song_bridge, "port_open", lambda *args, **kwargs: False)
    secret = "sk-bridge-test-secret-value"
    suno = "suno-bridge-test-secret-value"
    monkeypatch.setattr(kids_song_bridge.config, "OPENAI_API_KEY", secret)
    monkeypatch.setenv("SUNO_API_KEY", suno)
    report = kids_song_bridge.transfer_keys()
    captured = capsys.readouterr()
    dumped = __import__("json").dumps(report)
    assert secret not in dumped
    assert suno not in dumped
    assert secret not in captured.out
    assert suno not in captured.out
    assert secret not in captured.err
    text = env_file.read_text(encoding="utf-8")
    assert secret in text
    assert suno in text
    assert report["openai"] == "written"
    assert report["suno"] == "written"
    assert "sk-" not in report["message"]


def test_transfer_does_not_clobber_existing_or_blank_source(monkeypatch, tmp_path):
    studio = tmp_path / "studio"
    studio.mkdir()
    (studio / "package.json").write_text("{}", encoding="utf-8")
    env_file = studio / ".env"
    env_file.write_text('OPENAI_API_KEY="sk-already-set-by-user"\n', encoding="utf-8")
    monkeypatch.setenv("KIDS_SONG_STUDIO_DIR", str(studio))
    monkeypatch.setattr(kids_song_bridge, "port_open", lambda *args, **kwargs: False)
    monkeypatch.delenv("SUNO_API_KEY", raising=False)
    monkeypatch.setattr(kids_song_bridge.config, "OPENAI_API_KEY", "sk-new-should-not-land")
    report = kids_song_bridge.transfer_keys()
    text = env_file.read_text(encoding="utf-8")
    assert "sk-already-set-by-user" in text
    assert "sk-new-should-not-land" not in text
    assert report["openai"] == "unchanged"
    assert report["suno"] == "absent"

    monkeypatch.setattr(kids_song_bridge.config, "OPENAI_API_KEY", "")
    report_blank = kids_song_bridge.transfer_keys()
    assert report_blank["openai"] == "skipped"
    assert "sk-already-set-by-user" in env_file.read_text(encoding="utf-8")


def test_transfer_api_skips_present_key(monkeypatch, tmp_path):
    studio = tmp_path / "studio"
    studio.mkdir()
    (studio / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("KIDS_SONG_STUDIO_DIR", str(studio))
    monkeypatch.setattr(kids_song_bridge, "port_open", lambda *args, **kwargs: True)
    secret = "sk-bridge-api-secret-value"
    monkeypatch.setattr(kids_song_bridge.config, "OPENAI_API_KEY", secret)
    monkeypatch.delenv("SUNO_API_KEY", raising=False)
    calls = []

    def fake_request(method, path, body=None, form=None, timeout=12.0):
        calls.append((method, path))
        if method == "GET":
            return {"openaiKey": {"present": True, "masked": "••••abcd"}, "sunoKey": {"present": False}}
        raise AssertionError("must not post a key that is already present")

    monkeypatch.setattr(kids_song_bridge, "_studio_request", fake_request)
    report = kids_song_bridge.transfer_keys()
    dumped = __import__("json").dumps(report)
    assert secret not in dumped
    assert report["openai"] == "present"
    assert calls == [("GET", "/api/settings")]


def test_import_final_into_output(monkeypatch, tmp_path):
    studio = tmp_path / "studio"
    folder = studio / "projects" / "uzay" / "output"
    folder.mkdir(parents=True)
    source = folder / "final.mp4"
    source.write_bytes(b"not-a-real-mp4")
    output = tmp_path / "gallery"
    output.mkdir()
    monkeypatch.setenv("KIDS_SONG_STUDIO_DIR", str(studio))
    monkeypatch.setattr(kids_song_bridge.config, "OUTPUT_DIR", str(output))
    payload = kids_song_bridge.import_final_file(str(source), "uzay")
    assert payload["ok"] is True
    assert (output / payload["filename"]).read_bytes() == b"not-a-real-mp4"
    assert payload["filename"].startswith("cocuk_sarki_uzay")
    outside = tmp_path / "secret.mp4"
    outside.write_bytes(b"nope")
    rejected = kids_song_bridge.import_final_file(str(outside), "uzay")
    assert rejected["ok"] is False
