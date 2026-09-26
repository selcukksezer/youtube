import os
import pytest
from services.virality_evaluator import evaluate_script_virality, detect_script_slop_issues
from effects.smart_cropper import _parse_aspect_ratio
from services.youtube_clipper import YouTubeClipperService


def test_virality_evaluator_catches_slop():
    # Broken text that previously caused nonsense
    slop_text = (
        "Tek rakam: Stoacıların Öfkeyi Kontrol. "
        "Kleopatra'ın Stoacıların Öfkeyi Kontrol hakkında söylediği söz şok edici: "
        "Bu videonun sonunda hayatınızı değiştirecek o 3. kuralı duyacaksınız. "
        "Tek bir ayrıntı yeter. Tek bir ayrıntı yeter. "
        "Başa dön tek rakam: Stoacıların Öfkeyi."
    )
    issues = detect_script_slop_issues(slop_text)
    assert len(issues) > 0, "Should detect multiple slop phrases"
    audit = evaluate_script_virality(slop_text, topic="Stoacılık")
    assert audit["is_coherent"] is False, "Slop text must not be coherent"
    assert audit["score"] < 50, "Slop text must receive low virality score"


def test_virality_evaluator_rewards_quality():
    good_text = (
        "Neden tarihin en güçlü imparatoru Marcus Aurelius her sabah bir saat boyunca öfkesini eğitiyordu? "
        "Çoğu insan Stoacılığı duygusuzluk sanır, oysa gerçek tam tersi. "
        "Roma ordusu isyan ederken imparator tek bir kural uyguladı: Kontrol edemediğin hiçbir şeye öfkelenme. "
        "Bu basit zihinsel kural, 2000 yıl sonra bugün modern psikolojinin temelini oluşturuyor."
    )
    issues = detect_script_slop_issues(good_text)
    assert len(issues) == 0, "High quality text should have no slop issues"
    audit = evaluate_script_virality(good_text, topic="Marcus Aurelius")
    assert audit["is_coherent"] is True
    assert audit["score"] >= 70, f"Quality text should score high, got {audit['score']}"
    assert len(audit["signals_detected"]) >= 2


def test_smart_cropper_ratio():
    assert abs(_parse_aspect_ratio("9:16") - (9.0 / 16.0)) < 0.001
    assert abs(_parse_aspect_ratio("1:1") - 1.0) < 0.001


def test_clipper_service_instantiation():
    service = YouTubeClipperService()
    assert os.path.exists(service.download_dir)
    assert os.path.exists(service.output_dir)
