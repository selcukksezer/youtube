"""Embed the local Çocuk Şarkı MV studio inside this app."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import kids_song_bridge

router = APIRouter(tags=["Kids Song"])


class KidsProjectCreate(BaseModel):
    title: str = ""
    topic: str = ""
    lyrics: str = ""


def _json(body: dict):
    code = int(body.pop("status_code", 200 if body.get("ok") else 503))
    if code == 200:
        return body
    return JSONResponse(body, status_code=code)


@router.get("/api/kids-song/status")
def kids_song_status():
    return kids_song_bridge.status()


@router.post("/api/kids-song/start")
def kids_song_start():
    return kids_song_bridge.start()


@router.post("/api/kids-song/stop")
def kids_song_stop():
    return kids_song_bridge.stop_managed()


@router.post("/api/kids-song/settings/transfer")
def kids_song_transfer_keys():
    return kids_song_bridge.transfer_keys()


@router.get("/api/kids-song/projects")
def kids_song_projects():
    return _json(kids_song_bridge.list_projects())


@router.post("/api/kids-song/projects")
def kids_song_create_project(body: KidsProjectCreate):
    return _json(kids_song_bridge.create_project(body.title, body.topic, body.lyrics))


@router.get("/api/kids-song/projects/{project_id}")
def kids_song_project(project_id: str):
    return _json(kids_song_bridge.project_status(project_id))


@router.post("/api/kids-song/projects/{project_id}/import")
def kids_song_import(project_id: str):
    return _json(kids_song_bridge.import_project_final(project_id))


class KidsSongIdeaRequest(BaseModel):
    topic: str = "Sevimli Hayvanlar"
    age_group: str = "3-5"
    mood: str = "Neşeli"


@router.post("/api/kids-song/generate-song-idea")
def kids_song_generate_idea(body: KidsSongIdeaRequest):
    return kids_song_bridge.generate_kids_song_idea(body.topic, body.age_group, body.mood)

