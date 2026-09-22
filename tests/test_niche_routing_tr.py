"""Turkish topic → niche routing for all 35 niches (≥3 samples each)."""
import unittest

from director.visual_intent import resolve_niche_from_topic, resolve_topic_intelligence
from niche_templates import NICHES

# requested niche is deliberately wrong so regex/alias/fuzzy must win
_REQ = "1_news_flash"
_REQ_NEWS = "6_stoic_philosophy"

TR_TOPICS = {
    "1_news_flash": [
        "SON DAKİKA deprem haberi ankara",
        "flaş haber trafik kaza köprü",
        "gündem gelişme flaş açıklama",
    ],
    "2_reddit_confessions": [
        "AITA annem beni evden attı itiraf",
        "reddit confession işyerinde rezalet",
        "am I wrong kardeşime yalan söyledim",
    ],
    "3_split_gameplay": [
        "minecraft split screen hikaye",
        "subway surfers parkour gameplay",
        "split-screen parkour anlatı",
    ],
    "4_would_you_rather": [
        "tercih et uyumak mı yemek mi",
        "would you rather kırmızı hap mavi hap",
        "tercih et zengin olmak mı huzur mu",
    ],
    "5_guess_flag_country": [
        "bayrak tahmin oyunu hangi ülke",
        "ülke tahmin üç ipucu bayrak",
        "hangi ülke bu bayrak quiz",
    ],
    "6_stoic_philosophy": [
        "Marcus Aurelius stoacı kurallar",
        "seneca mektupları disiplin",
        "epiktetos stoacılık sabır",
    ],
    "7_dark_psychology": [
        "karanlık psikoloji manipülasyon işaretleri",
        "dark psychology beden dili yalan",
        "manipülasyon tuzak ikram psikoloji",
    ],
    "8_crypto_market": [
        "bitcoin fiyatı düştü kripto",
        "ethereum altcoin borsa analiz",
        "kripto piyasa bitcoin destek",
    ],
    "9_five_facts": [
        "biliyor muydunuz okyanus derinliği",
        "ilginç bilgi uzay kara delik",
        "mind blowing facts beyin uykusu",
    ],
    "10_religious_quotes": [
        "Hz Peygamber in en çok tekrar ettiği o dua bugün hayatınızı değiştirebilir",
        "kuran ayeti dini söz sabır",
        "hadis şerifi namaz sonrası zikir",
        "sahabe sünneti günlük dua",
        "Yasin suresi mealinden bir ayet",
        "Allah'ın en sevdiği ibadet nedir",
    ],
    "11_language_learning": [
        "ingilizce deyim günlük konuşma",
        "dil öğrenme 3 kalıp yabancı dil",
        "language hack günlük deyimleri",
    ],
    "12_amazon_affiliate": [
        "amazon ürün viral gadget mutfak",
        "trendyol life hack ürün üçlü",
        "affiliate ürün ev aleti inceleme",
    ],
    "13_mystery_paranormal": [
        "bermuda üçgeni ufo gizemi",
        "51. bölge paranormal dosya",
        "açıklanamayan ufo ışıkları",
    ],
    "14_movie_summaries": [
        "netflix film özeti spoiler",
        "ters köşe film önerisi sinema",
        "dizi tavsiye plot twist spoiler",
    ],
    "15_football_transfers": [
        "Mbappe transfer haberi",
        "Süper Lig bonservis bombası",
        "şampiyonlar ligi transfer listesi",
    ],
    "16_wealth_entrepreneurship": [
        "zengin olmak pasif gelir",
        "milyoner girişimci disiplin",
        "pasif gelir billionaire alışkanlık",
    ],
    "17_before_after_evolution": [
        "100 yıl önce evrim belgesel",
        "before after şehir dönüşümü",
        "then vs now teknoloji evrim belgesel",
    ],
    "18_astrology_horoscope": [
        "koç burcu astroloji yorumu",
        "haftalık burç horoskop aşk",
        "zodyak yükselen burç para",
    ],
    "19_historical_battles": [
        "tarihi savaş Osmanlı kuşatma",
        "savaş taktikleri Çanakkale",
        "history battle Napolyon taktik",
    ],
    "20_whatsapp_chat_story": [
        "whatsapp mesajları dram hikayesi",
        "sohbet ekranı chat story twisti",
        "mesaj hikayesi eski sevgili",
    ],
    "21_ai_tools_hacks": [
        "chatgpt yapay zeka ipuçları",
        "midjourney prompt gizli site",
        "ai araç ücretsiz chatgpt hile",
    ],
    "22_emoji_guess_game": [
        "emoji quiz film tahmin turu",
        "emoji oyunu hangi dizi",
        "guess the movie emoji üç ipucu",
    ],
    "23_fitness_nutrition_hacks": [
        "protein tozu fitness kas",
        "kilo ver yağ yakma tüyosu",
        "fitness spor diyet kahvaltı",
    ],
    "24_sigma_character_study": [
        "sigma gigachad karakter analizi",
        "lone wolf alpha male sessizlik",
        "sigma Thomas Shelby soğukkanlı",
    ],
    "25_celebrity_net_worth": [
        "ünlü serveti net worth listesi",
        "Elon kazanç net worth 2026",
        "ünlü serveti nasıl harcıyor",
    ],
    "26_dangerous_places": [
        "tehlikeli yerler yasak bölge",
        "forbidden places ölümcül ada",
        "yasak bölge ziyaret yasağı",
    ],
    "27_common_myths_busted": [
        "yanlış bilinen 5 mit",
        "doğru bilinen yanlış hurafe",
        "mit çürütme bilimsel gerçek su",
    ],
    "28_dream_meanings": [
        "rüyada yılan görmek tabiri",
        "rüya anlamı bilinçaltı su",
        "dream meaning diş düşmek",
    ],
    "29_optical_illusions_iq": [
        "optik illüzyon zeka testi",
        "optical illusion merkeze bak",
        "iq test beyin egzersizi illüzyon",
    ],
    "30_poetry_quotes": [
        "Nazım Hikmet şiir dinle",
        "Cemal Süreya aşk şiiri",
        "aşk şiiri gece okuma",
    ],
    "31_supercars_automotive": [
        "lamborghini süper araba",
        "ferrari hypercar hız rekoru",
        "süper araba motor sesi",
    ],
    "32_legal_consumer_hacks": [
        "tüketici hakları iade hakkı",
        "hukuki hak fatura itiraz",
        "vatandaş hakkı cayma süresi",
    ],
    "33_parenting_child_hacks": [
        "ebeveynlik çocuk psikolojisi uyku",
        "parenting hack öfbe nöbeti",
        "anne baba tüyosu sınır koyma",
    ],
    "34_gaming_easter_eggs": [
        "GTA sırları easter egg",
        "oyun sırrı gizli detay harita",
        "game secret zelda easter egg",
    ],
    "35_animal_kingdom_stories": [
        "hayvanlar alemi aslan avı",
        "vahşi hayvan belgesel kurt",
        "doğa belgeseli animal kingdom",
    ],
    "36_kids_animation": [
        "çocuk animasyon alfabe şarkısı",
        "kids cartoon yumuşak eğitim hayvan dostları",
        "çocuklar için animasyon ahlak hikayesi",
    ],
    "37_interactive_quiz": [
        "canlı quiz 3 saniyede bil",
        "interaktif quiz shorts challenge",
        "quiz shorts doğru cevabı yaz",
    ],
}


class TestNicheRoutingTr(unittest.TestCase):
    def test_all_36_niches_have_at_least_three_topics(self):
        self.assertEqual(len(NICHES), 37)
        self.assertEqual(set(TR_TOPICS), set(NICHES))
        for nid, topics in TR_TOPICS.items():
            self.assertGreaterEqual(len(topics), 3, nid)

    def test_turkish_topics_route_to_expected_niche(self):
        for nid, topics in TR_TOPICS.items():
            requested = _REQ_NEWS if nid == "1_news_flash" else _REQ
            for topic in topics:
                with self.subTest(niche=nid, topic=topic[:48]):
                    got = resolve_niche_from_topic(topic, requested)
                    self.assertEqual(got, nid, msg=f"{topic!r} -> {got}, want {nid}")

    def test_peygamber_dua_not_stoic(self):
        topic = "Hz Peygamber in en çok tekrar ettiği o dua bugün hayatınızı değiştirebilir"
        intel = resolve_topic_intelligence(topic, "6_stoic_philosophy")
        self.assertEqual(intel["resolved_niche"], "10_religious_quotes")
        self.assertIn(intel["match_method"], ("regex_lock", "alias", "fuzzy"))


if __name__ == "__main__":
    unittest.main()
