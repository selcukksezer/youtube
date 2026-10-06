import pytest
from plagiarism_checker import (
    _verbatim_phrase_overlap,
    _adjust_similarity_for_topic,
    check_script_originality,
    SIMILARITY_THRESHOLD,
)


def test_verbatim_phrase_overlap_identical():
    text1 = "Roma İmparatorluğu tarihin en güçlü ve en etkileyici medeniyetlerinden biriydi."
    text2 = "Roma İmparatorluğu tarihin en güçlü ve en etkileyici medeniyetlerinden biriydi."
    overlap = _verbatim_phrase_overlap(text1, text2)
    assert overlap > 0.8, f"Identical text overlap should be high, got {overlap}"


def test_verbatim_phrase_overlap_different_facts_same_subject():
    # Same subject (Ancient Rome), but completely distinct narrative sentences and facts
    text1 = (
        "Julius Caesar senatoda yirmi üç bıçak darbesiyle hayatını kaybetti. "
        "Brutus hançeri sapladığında Roma Cumhuriyeti ebediyen tarihe gömüldü. "
        "Halk sokaklara dökülerek isyan etti ve imparatorluk dönemi başladı."
    )
    text2 = (
        "Kolezyum kumlarında gladyatörler imparatoru selamlayarak vahşi aslanlarla savaşırdı. "
        "Tribünlerdeki binlerce Romalı başparmaklarını aşağı çevirerek mahkumların kaderini belirlerdi. "
        "Ekmek ve sirk politikası halkı yatıştırmak için kullanılan en etkili silahtı."
    )
    overlap = _verbatim_phrase_overlap(text1, text2)
    assert overlap < 0.10, f"Different facts should have near-zero verbatim overlap, got {overlap}"


def test_adjust_similarity_discounts_topic_vocabulary_when_content_is_unique():
    # High bag-of-words / TF-IDF overlap because both use Rome/Empire words, but distinct sentences
    raw_sim = 0.52
    body_sim = 0.48
    title1 = "Roma İmparatorluğunun En Büyük Gizemi"
    title2 = "Roma İmparatorluğunun En Karanlık Sırrı"
    
    text1 = "Julius Caesar senatoda yirmi üç bıçak darbesiyle hayatını kaybetti ve imparatorluk doğdu."
    text2 = "Kolezyum kumlarında gladyatörler vahşi aslanlarla savaşırdı ve halk tezahürat yapardı."

    adjusted = _adjust_similarity_for_topic(
        body_sim=body_sim,
        new_keyword="Roma İmparatorluğu",
        new_title=title1,
        entry_keyword="Roma İmparatorluğu",
        entry_title=title2,
        new_text=text1,
        entry_text=text2,
    )
    # Because verbatim overlap is near zero, adjusted similarity should be discounted below threshold
    assert adjusted < SIMILARITY_THRESHOLD, (
        f"Adjusted similarity should be discounted below {SIMILARITY_THRESHOLD}, got {adjusted}"
    )


def test_renamed_title_does_not_hide_copied_sentences():
    copied = (
        "Julius Caesar senatoda yirmi üç bıçak darbesiyle hayatını kaybetti. "
        "Brutus hançeri sapladığında Roma Cumhuriyeti ebediyen tarihe gömüldü. "
        "Halk sokaklara dökülerek isyan etti ve imparatorluk dönemi başladı."
    )
    adjusted = _adjust_similarity_for_topic(
        body_sim=0.2,
        new_keyword="Gladyatör ekmeği",
        new_title="Sirk politikası nasıl çalıştı",
        entry_keyword="Roma İmparatorluğu",
        entry_title="Roma İmparatorluğunun En Büyük Gizemi",
        new_text=copied,
        entry_text=copied,
    )
    assert adjusted > SIMILARITY_THRESHOLD


def test_other_channel_script_does_not_block():
    from plagiarism_checker import add_script_to_db, clear_plagiarism_db
    clear_plagiarism_db()
    script = (
        "Balinalar uyurken beyinlerinin sadece bir yarısını dinlendirir ve diğer yarısıyla nefes almaya devam eder. "
        "Bu olağanüstü biyolojik mekanizma onların boğulmasını önler ve sürüyü bir arada tutar."
    )
    add_script_to_db(script, keyword="balina", title="Balina uykusu", channel_slug="channel_a", render_status="completed")
    other_ok, _other_sim, _other_match = check_script_originality(
        script, keyword="balina", title="Balina uykusu", channel_slug="channel_b",
    )
    same_ok, same_sim, _same_match = check_script_originality(
        script, keyword="balina", title="Balina uykusu", channel_slug="channel_a",
    )
    clear_plagiarism_db()
    assert other_ok is True
    assert same_ok is False
    assert same_sim >= SIMILARITY_THRESHOLD


def test_allow_similar_script_bypasses_similarity_gate():
    text = "Aynı konu ve aynı cümleler tekrar tekrar kopyalanıp kullanılıyor."
    
    # Check with allow_similar_script=True
    approved, sim, matched = check_script_originality(
        text,
        keyword="Test Konu",
        title="Test Konu",
        allow_similar_script=True,
    )
    assert approved is True, "Script with allow_similar_script=True must be approved regardless of similarity"
