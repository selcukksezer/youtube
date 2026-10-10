import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import config
from scenes.scripts import generate_reddit_rewrite_script
from scenes.scripts import _reddit_script_issues


def _valid_plan():
    return {
        "title": "Telefonumdaki mesaj gerçeği ortaya çıkardı",
        "scenes": [
            {"narration": text}
            for text in (
                "Bunu anlatmak benim için kolay değil ama artık bu hikâyeyi tek başıma taşımak istemiyorum.",
                "Düğüne hazırlanırken nişanlımın telefonunda daha önce hiç görmediğim bir mesajla karşılaştım.",
                "Mesajdaki tarih, bana daha önce anlattığı hikâyeyle uyuşmuyordu ve şüphelerimi artırıyordu.",
                "Önce yanlış anlamış olabileceğimi düşündüm, bu yüzden konuşmayı en başından dikkatle tekrar okudum.",
                "Sonra aynı kişinin adını eski bir fotoğrafta da gördüm ve içimdeki kuşku büyüdü.",
                "Bunu sakin bir şekilde sorduğumda verdiği yanıt, şüphelerimi daha da artırmış oldu.",
                "Düğünü erteleyip önce gerçeği öğrenmem gerektiğine karar verdim ve bunu ona açıkça söyledim.",
                "Siz benim yerimde olsaydınız, bu durumda nasıl bir karar verirdiniz ve neden?",
            )
        ],
    }


class RedditScriptQualityTests(unittest.TestCase):
    def test_rejects_rendered_script_fragments_and_repeated_title_hook(self):
        title = "Nişanlımın telefonundaki kör noktayı buldum ve düğünü iptal etmek için sadece 48 saat var"
        narrations = [
            "Bunu bilmeden geçen her gün, Nişanlımın telefonundaki kör noktayı buldum ve düğünü iptal etmek.",
            "İlk kilit detay, telefonundaki mesajları saklamasıydı ve bu davranış beni şüphelendirdi.",
            "İkinci kilit nokta, bana verdiği açıklamanın kayıtlarla hiç uyuşmamasıydı.",
            "Üçüncü ve en çarpıcı bulgu ise sakladığı belgelerin.",
            "Bu durum ilişkinin temelindeki güven sorununu ve saklanan gerçeği gözler önüne.",
            "Onunla konuşmadan önce elimdeki bilgileri yeniden dikkatlice kontrol ettim.",
            "Karar vermek için kendime biraz zaman tanıdım ve olanları düşündüm.",
            "Siz olsaydınız bu durumda nasıl davranırdınız, yorumlarda anlatır mıydınız?",
        ]
        plan = {
            "title": title,
            "scenes": [{"narration": text} for text in narrations],
        }

        issues = _reddit_script_issues(plan)

        self.assertIn("hook_repeats_title", issues)
        self.assertIn("repetitive_numbered_filler", issues)
        self.assertTrue(any(issue.endswith("incomplete_clause") for issue in issues))
        self.assertTrue(any(issue.endswith("unfinished_possessive") for issue in issues))

    def test_accepts_distinct_complete_narration(self):
        self.assertEqual(_reddit_script_issues(_valid_plan()), [])

    def test_retries_ai_script_after_quality_rejection(self):
        title = "Nişanlımın telefonundaki kör noktayı buldum ve düğünü iptal etmek için sadece 48 saat var"
        invalid_plan = {
            "title": title,
            "scenes": [
                {"narration": text}
                for text in (
                    "Bunu bilmeden geçen her gün, Nişanlımın telefonundaki kör noktayı buldum ve düğünü iptal etmek.",
                    "İlk kilit detay, telefonundaki mesajları saklamasıydı ve bu davranış beni şüphelendirdi.",
                    "İkinci kilit nokta, bana verdiği açıklamanın kayıtlarla hiç uyuşmamasıydı.",
                    "Üçüncü ve en çarpıcı bulgu ise sakladığı belgelerin.",
                    "Bu durum ilişkinin temelindeki güven sorununu ve saklanan gerçeği gözler önüne.",
                    "Onunla konuşmadan önce elimdeki bilgileri yeniden dikkatlice kontrol ettim.",
                    "Karar vermek için kendime biraz zaman tanıdım ve olanları düşündüm.",
                    "Siz olsaydınız bu durumda nasıl davranırdınız, yorumlarda anlatır mıydınız?",
                )
            ],
        }

        def response(plan):
            message = SimpleNamespace(content=json.dumps(plan, ensure_ascii=False))
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        with patch("openai.OpenAI"), \
             patch("scenes.generator._call", side_effect=[response(invalid_plan), response(_valid_plan())]) as call, \
             patch.object(config, "AI_PROVIDER", "OpenAI"), \
             patch.object(config, "AI_API_KEY", "test-key"), \
             patch.object(config, "AI_BASE_URL", ""), \
             patch.object(config, "AI_MODEL", "test-model"), \
             patch.object(config, "_P", [], create=True):
            result = generate_reddit_rewrite_script(
                {"title": title, "body": "A source story about a hidden message."},
                lang="tr",
            )

        self.assertEqual(call.call_count, 2)
        retry_params = call.call_args_list[1].args[1]
        self.assertIn("kalite sorunları nedeniyle reddedildi", retry_params["messages"][1]["content"])
        self.assertIn("hook_repeats_title", retry_params["messages"][1]["content"])
        self.assertEqual(result["title"], title)


if __name__ == "__main__":
    unittest.main()
