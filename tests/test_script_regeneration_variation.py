import pytest
from fastapi.testclient import TestClient
from server import app
from scenes.generator import generate_scenes


def test_generate_scenes_returns_different_narrations_on_regeneration():
    topic = "Hz. Peygamber'in en çok tekrar ettiği o dua bugün hayatınızı değiştirebilir."
    
    plan1 = generate_scenes(
        title=topic,
        niche_type="10_religious_quotes",
        language="tr",
        variation_attempt=0,
        force_regenerate=False,
    )
    
    plan2 = generate_scenes(
        title=topic,
        niche_type="10_religious_quotes",
        language="tr",
        variation_attempt=1,
        previous_narration=plan1.get("full_narration", ""),
        force_regenerate=True,
    )
    
    plan3 = generate_scenes(
        title=topic,
        niche_type="10_religious_quotes",
        language="tr",
        variation_attempt=2,
        previous_narration=plan2.get("full_narration", ""),
        force_regenerate=True,
    )

    narr1 = plan1.get("full_narration", "")
    narr2 = plan2.get("full_narration", "")
    narr3 = plan3.get("full_narration", "")

    assert narr1 != narr2, "Second generation must produce a different script variation than first"
    assert narr2 != narr3, "Third generation must produce a different script variation than second"
    assert narr1 != narr3, "Third generation must differ from first"


def test_api_script_generate_with_force_regenerate():
    client = TestClient(app)
    topic = "Karanlık Psikoloji Beden Dili İpuçları"

    res1 = client.post("/api/script/generate", json={
        "keyword": topic,
        "niche": "7_dark_psychology",
        "language": "tr",
        "force_regenerate": False,
        "variation_attempt": 0,
    })
    assert res1.status_code == 200, res1.text
    data1 = res1.json()
    assert data1["status"] == "ok"
    narr1 = data1["plan"].get("full_narration", "")

    res2 = client.post("/api/script/generate", json={
        "keyword": topic,
        "niche": "7_dark_psychology",
        "language": "tr",
        "force_regenerate": True,
        "variation_attempt": 1,
        "previous_narration": narr1,
    })
    assert res2.status_code == 200, res2.text
    data2 = res2.json()
    assert data2["status"] == "ok"
    narr2 = data2["plan"].get("full_narration", "")

    assert narr1 != narr2, "API with force_regenerate=True must produce a distinct narrative than previous"
