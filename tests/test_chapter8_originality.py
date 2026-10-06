"""
Bölüm 8.1 Testleri: SQLite Tabanlı Çapraz Senaryo Özgünlük Doğrulaması (Madde 120)
(SQLite-backed Cross-Script Originality Verification)
- SQLite generated_scripts tablosu kayıt ve çekme
- Kanal izolasyonu (channel_slug) ve limit kontrolü
- %35 benzerlik eşiği (Jaccard token overlap)
- check_script_originality (Tuple[bool, float]) sözleşmesi
- check_script_originality_detailed ve matched_snippet
- plagiarism_checker ve compliance/originality entegrasyonu
"""
import unittest
import database
from compliance.originality import (
    check_script_originality,
    check_script_originality_detailed,
    register_approved_script,
    tokenize_script,
    calculate_jaccard_overlap,
)
from plagiarism_checker import (
    check_script_originality as legacy_check_originality,
    add_script_to_db as legacy_add_script,
)


class TestChapter8ScriptOriginality(unittest.TestCase):

    def setUp(self):
        # Test için veritabanını başlat ve test kanallarını temizle
        database.init_db()
        with database.get_connection() as conn:
            conn.execute("DELETE FROM generated_scripts WHERE channel_slug LIKE 'test_%'")
            conn.commit()

    def test_tokenize_and_jaccard_overlap(self):
        """Tokenizasyon ve Jaccard örtüşme oranının doğru hesaplandığı testi."""
        tokens_a = tokenize_script("Marcus Aurelius Roma imparatoru ve stoacı filozoftur.")
        tokens_b = tokenize_script("Marcus Aurelius Roma imparatorluğunda bilge bir filozoftur.")
        
        # Ortak tokenlar: marcus, aurelius, roma, filozoftur
        overlap = calculate_jaccard_overlap(tokens_a, tokens_b)
        self.assertGreater(overlap, 0.30)
        self.assertLessEqual(overlap, 1.0)

        # Tamamen farklı metinler
        tokens_c = tokenize_script("Kripto para borsalarında Bitcoin rekor kırdı ve yükseldi.")
        diff_overlap = calculate_jaccard_overlap(tokens_a, tokens_c)
        self.assertLess(diff_overlap, 0.10)

    def test_sqlite_script_persistence_and_channel_isolation(self):
        """SQLite generated_scripts tablosuna kayıt, çekme ve kanal izolasyonu testi."""
        chan_a = "test_channel_tech"
        chan_b = "test_channel_history"

        script_tech = "Yapay zeka modelleri 2026 yılında yazılım sektörünü kökten değiştirdi ve otomasyon hızlandı."
        script_hist = "Büyük İskender antik çağda Asya seferine çıkarak Persepolis şehrini fethetti."

        # Kaydet
        id_a = database.save_generated_script(
            script_text=script_tech,
            title="AI 2026 Devrimi",
            keyword="yapay zeka",
            channel_slug=chan_a,
        )
        self.assertGreater(id_a, 0)

        id_b = database.save_generated_script(
            script_text=script_hist,
            title="Büyük İskender Seferi",
            keyword="iskender",
            channel_slug=chan_b,
        )
        self.assertGreater(id_b, 0)

        # Çek ve kanal filtrelerini doğrula
        scripts_a = database.get_recent_scripts(channel_slug=chan_a, limit=10)
        self.assertIn(script_tech, scripts_a)

        # chan_a geçmişinde chan_b'nin özel senaryosu olmamalı (kanal izolasyonu)
        scripts_b = database.get_recent_scripts(channel_slug=chan_b, limit=10)
        self.assertIn(script_hist, scripts_b)

    def test_check_script_originality_plan_contract(self):
        """plan.md 8.1 Tuple[bool, float] sözleşmesinin doğrulanması testi."""
        test_slug = "test_chan_contract"
        
        base_script = (
            "Güneş sistemindeki en büyük volkan Mars gezegeninde bulunan Olympus Mons dağıdır. "
            "Bu dağın yüksekliği Everest'in tam üç katıdır ve uzaydan bile rahatça görülebilir."
        )
        
        # 1. İlk kayıt: henüz DB'de yok, onaylanmalı
        is_ok, score = check_script_originality(base_script, channel_slug=test_slug, threshold=0.35)
        self.assertTrue(is_ok)
        self.assertEqual(score, 0.0)

        # Kaydet
        register_approved_script(
            script_text=base_script,
            title="Mars Olympus Mons",
            keyword="mars volkan",
            channel_slug=test_slug,
        )

        # 2. Tam kopya veya yüksek örtüşmeli senaryo (%35 üstü): REDDEDİLMELİ
        duplicate_script = (
            "Güneş sistemindeki en büyük devasa volkan Mars gezegeninde bulunan Olympus Mons dağıdır. "
            "Bu heybetli dağın yüksekliği Everest'in üç katıdır ve uzaydan görülebilir."
        )
        is_dup_ok, dup_score = check_script_originality(duplicate_script, channel_slug=test_slug, threshold=0.35)
        self.assertFalse(is_dup_ok, f"Duplicate should fail! Got score: {dup_score}")
        self.assertGreater(dup_score, 0.35)

        # 3. Tamamen özgün farklı senaryo: ONAYLANMALI
        unique_script = (
            "Derin okyanus çukurlarında yaşayan fener balıkları karanlık sularda kendi ışıklarını üreterek avlanırlar. "
            "Baskı insan vücudunu anında ezebilecek güçtedir."
        )
        is_uniq_ok, uniq_score = check_script_originality(unique_script, channel_slug=test_slug, threshold=0.35)
        self.assertTrue(is_uniq_ok)
        self.assertLess(uniq_score, 0.35)

    def test_check_script_originality_detailed_and_snippet(self):
        """Detaylı kontrolde en çok benzeyen senaryonun özetini döndürdüğü testi."""
        test_slug = "test_chan_detailed"
        original = "Tarihin ilk denizaltı denemeleri Osmanlı döneminde Tahtelbahir ile timsah şeklinde yapılmıştır."
        
        register_approved_script(
            script_text=original,
            title="Osmanlı Denizaltısı",
            channel_slug=test_slug,
        )

        similar = "Tarihin ilk denizaltı denemeleri Osmanlı zamanında Tahtelbahir adı verilen araçla yapılmıştır."
        is_ok, overlap, snippet = check_script_originality_detailed(
            similar, channel_slug=test_slug, threshold=0.35
        )
        self.assertFalse(is_ok)
        self.assertGreater(overlap, 0.35)
        self.assertIsNotNone(snippet)
        self.assertIn("Tahtelbahir", snippet)

    def test_plagiarism_checker_sqlite_integration(self):
        """plagiarism_checker.py modülünün SQLite kayıtlarını da başarıyla taradığı testi."""
        test_slug = "test_chan_legacy"
        orig_text = (
            "Balinalar uyurken beyinlerinin sadece bir yarısını dinlendirir ve diğer yarısıyla nefes almaya devam eder. "
            "Bu olağanüstü biyolojik mekanizma onların boğulmasını önler."
        )
        
        legacy_add_script(orig_text, title="Balinaların Uykusu", keyword="balina", channel_slug=test_slug)

        # Aynı metni legacy check_script_originality ile kontrol et
        is_orig, sim, matched = legacy_check_originality(
            orig_text,
            keyword="balina",
            channel_slug=test_slug,
        )
        self.assertFalse(is_orig)
        self.assertGreaterEqual(sim, 0.45)


if __name__ == "__main__":
    unittest.main()
