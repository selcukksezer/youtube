"""
Tests for scenario production contract and fallback quality validation:
Verifies that procedural fallbacks, timeline solving, and quality gates
cooperate seamlessly without false-positive 'words_below_12' hard-fails.
"""
import pytest
from production.quality import validate_script_quality
from scenes.fallback import _generate_procedural_fallback_scenes
from director.compiler import compile_director_plan
from director.schema import shorts_word_budget


def test_stoic_fallback_meets_production_contract():
    """
    Verify that the fallback fits the natural TTS word budget and duration
    without hard-failing quality gates; 120+ words remain an advisory target.
    """
    topic = "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı"
    plan = _generate_procedural_fallback_scenes(topic, niche_type="6_stoic_philosophy", language="tr")

    assert "scenes" in plan
    scenes = plan["scenes"]
    assert 6 <= len(scenes) <= 12

    # Compile with director to simulate full production timeline solving
    director = compile_director_plan(
        plan,
        title=topic,
        niche_id="6_stoic_philosophy",
        language="tr",
    )
    compiled_plan = director.to_legacy_plan()

    # Run production quality gate
    quality = validate_script_quality(compiled_plan)
    assert not quality["hard_fail"], f"Production contract failed: {quality.get('issues')}"
    assert quality["duration"] >= 45.0
    assert quality["duration"] <= 60.25
    assert 6 <= quality["scene_count"] <= 12
    assert 85 <= quality["word_count"] <= shorts_word_budget()
    if quality["word_count"] < 120:
        assert any(
            warning.startswith("word_count_below_optimal:")
            for warning in quality["warnings"]
        )


def test_quality_gate_advisory_vs_hard_fail():
    """
    Verify that short scenes (7-11 words) in fast-paced cuts produce advisory warnings
    rather than hard-blocking the render, while true fragments (<7 words) still hard fail.
    """
    # Plan with unique scenes and total words > 120, including a 7-word punchline scene
    mock_sentences = [
        "Marcus Aurelius Meditations kitabında öfkeyi kontrol altına almanın en temel yollarını açıkça yazmıştır.",
        "Seneca insanın çoğu zaman gerçekte olandan çok kendi zihninde kurduğu senaryolarda acı çektiğini belirtir.",
        "Dış olaylar senin kontrolünde olmayabilir fakat verdiğin tepki tamamen senin kişisel iradene ve ahlakına aittir.",
        "Günün ilk saatlerinde karşılacağın zorlukları birer engel değil zihnini güçlendirecek antrenmanlar olarak kabul et.",
        "Öfke zihnini ele geçirdiğinde karar alma yeteneğini felç eden ve seni hataya sürükleyen bir zehirdir.",
        "Sessizlik ve derin nefes çoğu kriz anında en güçlü ve en sarsılmaz stratejik savunma hattıdır.",
        "Kendi merkezini sağlam tuttuğun sürece dışarıdaki hiçbir fırtına veya provokasyon senin ruhunu sarsamaz.",
        "Kadim bilgelerin öğrettiği en temel prensip budur ve yüzyıllardır geçerliliğini asla ve asla kaybetmemiştir.",
        "Ve tam da bu yüzden asla durma.",  # 7 words -> valid fast-paced cut!
    ]
    plan_with_pacing = {
        "scenes": [
            {
                "narration": mock_sentences[i],
                "scene_description": f"Unique visual setting {i} depicting ancient stoic philosophy and marble sculpture",
                "search_queries": [f"query {i} a", f"query {i} b"],
                "duration": 5.2,
            }
            for i in range(len(mock_sentences))
        ]
    }
    q_valid = validate_script_quality(plan_with_pacing)
    assert not q_valid["hard_fail"], f"Pacing scene should not hard-fail: {q_valid.get('issues')}"
    assert any("words_below_12" in w for w in q_valid.get("warnings", []))


    # Plan with a 4-word fragment (real defect)
    plan_with_fragment = {
        "scenes": [
            {
                "narration": "Evet tam olarak.",  # 3 words -> fatal fragment!
                "scene_description": "Ancient Roman statue under dramatic studio lighting with dust particles",
                "search_queries": ["marcus aurelius statue", "ancient rome sculpture"],
                "duration": 5.0,
            }
        ]
        + [
            {
                "narration": "Marcus Aurelius Meditations kitabında öfkeyi kontrol altına almanın en temel yollarını açıkça yazmıştır.",
                "scene_description": "Ancient Roman statue under dramatic studio lighting with dust particles",
                "search_queries": ["marcus aurelius statue", "ancient rome sculpture"],
                "duration": 5.0,
            }
            for _ in range(8)
        ]
    }
    q_invalid = validate_script_quality(plan_with_fragment)
    assert q_invalid["hard_fail"]
    assert any("words_below_7" in i for i in q_invalid["issues"])


def test_word_count_111_and_fillers_do_not_hard_fail():
    """
    Verify that a script with ~111 words and typical hooks/fillers
    (e.g., 'bunu aklında tut', 'takipte kalın') produces advisory warnings
    rather than a fatal QualityGate rejection.
    """
    scenes = [
        {
            "narration": "Bilim insanlarının bile açıklayamadığı bu esrarengiz olay tüylerinizi ürpertecek.",
            "scene_description": "Mysterious cosmic event in deep space with glowing anomalies",
            "search_queries": ["deep space mystery", "cosmic phenomenon anomaly"],
            "duration": 5.5,
        },
        {
            "narration": "Okyanusun en derin noktasında kaydedilen bu tuhaf sesler henüz tam olarak aydınlatılamadı.",
            "scene_description": "Deep ocean trench with murky dark blue water and light rays",
            "search_queries": ["deep sea trench mystery", "underwater anomaly exploration"],
            "duration": 5.5,
        },
        {
            "narration": "Araştırmacılar yüzlerce metre derinlikte daha önce hiç görülmemiş devasa yapılar buldular.",
            "scene_description": "Underwater research submarine exploring mysterious underwater structures",
            "search_queries": ["underwater structure ruins", "submersible deep ocean"],
            "duration": 5.5,
        },
        {
            "narration": "Bunu aklında tut çünkü tarih kitaplarında anlatılanlar gerçeğin sadece ufak bir kısmı olabilir.",  # filler hook
            "scene_description": "Ancient dusty books and secret manuscripts in a dark candlelit library",
            "search_queries": ["ancient library secret manuscript", "dark mysterious archive"],
            "duration": 5.5,
        },
        {
            "narration": "Eski uygarlıkların geride bıraktığı haritalarda bugün var olmayan adalar ve kıtalar açıkça çizilmiştir.",
            "scene_description": "Vintage navigational parchment map showing unknown lost continents",
            "search_queries": ["vintage world map parchment", "ancient cartography explorer"],
            "duration": 5.5,
        },
        {
            "narration": "Uydu fotoğrafları Antarktika buzullarının altında gizlenmiş kusursuz geometrik piramit benzeri yapılar gösteriyor.",
            "scene_description": "Satellite aerial view of Antarctica glaciers revealing geometric anomaly",
            "search_queries": ["antarctica glacier satellite pyramid", "aerial icy continent mystery"],
            "duration": 5.5,
        },
        {
            "narration": "Bilim dünyası bu keşiflerin tesadüf olduğunu söylese de şüpheler her geçen gün artıyor.",
            "scene_description": "Laboratory scientists discussing baffling satellite data on high tech screens",
            "search_queries": ["scientists looking at screens", "laboratory research baffled"],
            "duration": 5.5,
        },
        {
            "narration": "Daha fazlası için takipte kalın ve kendi düşüncelerinizi mutlaka paylaşın.",  # filler hook
            "scene_description": "Dramatic sunset over horizon with silhouette of thinker questioning reality",
            "search_queries": ["dramatic cinematic sunset horizon", "silhouette looking at sky"],
            "duration": 5.5,
        },
    ]

    plan = {"scenes": scenes}
    report = validate_script_quality(plan)

    # Word count is around 90-120 words
    assert 85 <= report["word_count"] <= 130
    # Must NOT be a hard fail!
    assert not report["hard_fail"], f"Should not hard fail, but got issues: {report.get('issues')}"
    assert report["action"] == "RENDER_ALLOWED"
    # Warnings should mention the filler advisory, not block rendering
    assert any("mechanical_filler" in w for w in report.get("warnings", []))
