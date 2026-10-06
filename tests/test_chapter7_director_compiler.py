"""
Bölüm 7.6 Testleri: DirectorPlan Derleyici ve Sahne Niyeti Eşleme
(DirectorPlan Compiler & Scene Intent Mapping)
- Her sahnenin bağımsız DirectorScene nesnesi olarak derlenmesi
- Sahne süresi, anlatım metni, kamera yönü, görsel arama sorguları ve görsel niyet etiketleri
- 'establishing', 'closeup', 'action', 'transition' niyet sınıflandırması
- Kamera hareket yönü çeşitliliği ve ardışık tekrar önleme (Variety safeguard)
- FFmpeg Ken Burns & Zoompan entegrasyonu
"""
import unittest
from typing import Dict, Any, List

from director.schema import (
    DirectorPlan,
    ScenePlan,
    DirectorScene,
    SCENE_INTENTS,
    CAMERA_DIRECTIONS,
)
from director.compiler import compile_director_plan
from director.visual_intent import (
    classify_scene_intent,
    assign_camera_direction,
    apply_visual_intents,
)
from director.validate import validate_director_plan
from render.ffmpeg_graph import cheap_pan_filter, zoompan_filter


class TestChapter7DirectorCompiler(unittest.TestCase):

    def test_director_scene_alias_and_attributes(self):
        """DirectorScene nesnesinin ScenePlan ile eşdeğer olduğu ve tüm zorunlu alanları taşıdığı testi."""
        self.assertIs(DirectorScene, ScenePlan)

        # Temel nesne oluşturma
        scene = DirectorScene(
            index=0,
            narration="Antik Roma'nın kalbinde tarihin en büyük imparatorluğu yükseliyordu.",
            duration=4.5,
            scene_intent="establishing",
            camera_direction="zoom_out",
            search_queries=["ancient rome forum dusk", "roman marble columns"],
        )

        self.assertEqual(scene.index, 0)
        self.assertEqual(scene.duration, 4.5)
        self.assertIn(scene.scene_intent, SCENE_INTENTS)
        self.assertIn(scene.camera_direction, CAMERA_DIRECTIONS)
        self.assertEqual(len(scene.search_queries), 2)

        # Serileştirme ve geri yükleme
        data = scene.to_dict()
        self.assertEqual(data["scene_intent"], "establishing")
        self.assertEqual(data["camera_direction"], "zoom_out")

        restored = DirectorScene.from_dict(data)
        self.assertEqual(restored.scene_intent, "establishing")
        self.assertEqual(restored.camera_direction, "zoom_out")

    def test_scene_intents_and_camera_directions_constants(self):
        """Kanonik niyet ve kamera yönü sabitlerinin eksiksiz tanımlandığı testi."""
        self.assertTrue({"establishing", "closeup", "action", "transition"}.issubset(set(SCENE_INTENTS)))
        self.assertTrue(all(d in CAMERA_DIRECTIONS for d in [
            "zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "static"
        ]))

    def test_classify_scene_intent_semantic_mapping(self):
        """Anlamsal anahtar kelimelere ve anlatı konumuna göre doğru niyet sınıflandırması testi."""
        # 1. Açılış sahnesi (Genel / Manzara -> establishing)
        intent_hook_wide = classify_scene_intent(
            narration="Tarihte bilinen bütün imparatorlukların en güçlüsü burada kuruldu.",
            index=0,
            total_scenes=6,
        )
        self.assertEqual(intent_hook_wide, "establishing")

        # 2. Açılış sahnesi (Şok / Yüz / Sır -> closeup)
        intent_hook_close = classify_scene_intent(
            narration="Bu adamın yüzündeki sırra ve gözlerine dikkatli bakın.",
            index=0,
            total_scenes=6,
        )
        self.assertEqual(intent_hook_close, "closeup")

        # 3. Aksiyon sahnesi (Hareket / Çatışma / Hız -> action)
        intent_action = classify_scene_intent(
            narration="Askerler hızla siperden fırladı ve düşman hattına doğru hücum etti.",
            index=2,
            total_scenes=6,
        )
        self.assertEqual(intent_action, "action")

        # 4. Yakın plan sahnesi (Detay / Belge / Yüz -> closeup)
        intent_closeup = classify_scene_intent(
            narration="Eski parşömen üzerindeki gizli mührü inceledi ve elindeki mektubu okudu.",
            index=3,
            total_scenes=6,
        )
        self.assertEqual(intent_closeup, "closeup")

        # 5. Geçiş sahnesi (Zaman / Köprü / Dönüşüm -> transition)
        intent_trans = classify_scene_intent(
            narration="Ancak yıllar sonra her şey tamamen değişti ve yeni bir dönem başladı.",
            index=4,
            total_scenes=6,
        )
        self.assertEqual(intent_trans, "transition")

        # 6. Son sahne (Döngü köprüsü / Kapanış -> transition)
        intent_outro = classify_scene_intent(
            narration="İşte bu yüzden tarihin en büyük sırrı sonsuza dek saklı kaldı.",
            index=5,
            total_scenes=6,
        )
        self.assertEqual(intent_outro, "transition")

    def test_assign_camera_direction_and_alternation(self):
        """Kamera yönünün niyete uygun seçildiği ve ardışık sahnelerde çeşitliliğin korunduğu testi."""
        prev = None
        for i, intent in enumerate(["establishing", "closeup", "action", "transition", "action"]):
            cam = assign_camera_direction(intent, index=i, prev_direction=prev)
            self.assertIn(cam, CAMERA_DIRECTIONS)
            if prev is not None:
                self.assertNotEqual(cam, prev, f"Scene {i} repeated previous camera direction {prev}")
            prev = cam

    def test_compile_director_plan_integration(self):
        """compile_director_plan derleyicisinin tüm sahneleri DirectorScene olarak eksiksiz ürettiği testi."""
        raw_plan = {
            "title": "Stoacı Felsefe ve Marcus Aurelius",
            "niche_id": "2_philosophy_stoic",
            "scenes": [
                {
                    "index": 0,
                    "narration": "Antik Roma sokaklarında imparator Marcus Aurelius derin düşüncelere daldı.",
                    "scene_description": "Roman marble columns and imperial statues under dusk light.",
                    "duration": 4.0,
                },
                {
                    "index": 1,
                    "narration": "Gözlerini kapattı ve elindeki eski parşömene şu sözleri yazdı.",
                    "scene_description": "Close up of hands writing with quill on ancient parchment scroll.",
                    "duration": 3.8,
                },
                {
                    "index": 2,
                    "narration": "Düşman orduları sınıra hızla hücum ederken o sükunetini korudu.",
                    "scene_description": "Warriors riding horses fast across dusty battlefield.",
                    "duration": 4.2,
                },
                {
                    "index": 3,
                    "narration": "Ancak zafer kılıçla değil, zihnin dinginliğiyle kazanıldı.",
                    "scene_description": "Calm ocean horizon sunrise with stoic philosopher standing alone.",
                    "duration": 4.5,
                },
            ],
        }

        plan = compile_director_plan(raw_plan, title=raw_plan["title"], niche_id=raw_plan["niche_id"])

        self.assertIsInstance(plan, DirectorPlan)
        self.assertGreaterEqual(len(plan.scenes), 4)

        prev_cam = None
        for i, sc in enumerate(plan.scenes):
            # Her sahne DirectorScene sözleşmesine uymalı
            self.assertIsInstance(sc, DirectorScene)
            self.assertGreater(sc.duration, 0.5)
            self.assertTrue(bool(sc.narration.strip()))
            self.assertIn(sc.scene_intent, SCENE_INTENTS)
            self.assertIn(sc.camera_direction, CAMERA_DIRECTIONS)
            self.assertTrue(len(sc.search_queries) > 0)
            self.assertTrue(bool(sc.visual_intent.action))

            # Ardışık kamera yönü çeşitliliği
            if prev_cam is not None:
                self.assertNotEqual(sc.camera_direction, prev_cam, f"Scene {i} repeated camera direction {prev_cam}")
            prev_cam = sc.camera_direction

        # Legacy plan çıktısında alanların korunumu
        legacy = plan.to_legacy_plan()
        for sdict in legacy["scenes"]:
            self.assertIn("scene_intent", sdict)
            self.assertIn("camera_direction", sdict)
            self.assertIn(sdict["scene_intent"], SCENE_INTENTS)
            self.assertIn(sdict["camera_direction"], CAMERA_DIRECTIONS)

    def test_validate_director_plan_checks(self):
        """validate_director_plan fonksiyonunun scene_intent ve camera_direction denetimi testi."""
        plan = DirectorPlan(
            title="Test Video",
            niche_id="1_news_flash",
            full_narration="Bir test anlatımı cümlesi burada yer alıyor.",
            scenes=[
                DirectorScene(
                    index=0,
                    narration="Test anlatımı",
                    duration=4.0,
                    scene_intent="invalid_intent_xyz",
                    camera_direction="invalid_cam_123",
                    search_queries=["test query"],
                )
            ],
        )

        res = validate_director_plan(plan)
        # Uyarı listesinde geçersiz intent ve camera_direction yer almalı
        intent_warn = any("geçersiz scene_intent" in w for w in res["warnings"])
        cam_warn = any("geçersiz camera_direction" in w for w in res["warnings"])
        self.assertTrue(intent_warn)
        self.assertTrue(cam_warn)

    def test_ffmpeg_camera_direction_filters(self):
        """FFmpeg cheap_pan_filter ve zoompan_filter'ın kamera yönlerini doğru işlediği testi."""
        # cheap_pan_filter testleri
        for cam_dir in ["pan_right", "pan_left", "tilt_down", "tilt_up", "zoom_in", "zoom_out", "static"]:
            f = cheap_pan_filter(1080, 1920, 3.5, scene_index=0, camera_direction=cam_dir)
            self.assertIn("scale=", f)
            self.assertIn("crop=", f)
            self.assertIn("1080:1920", f)

        # zoompan_filter testleri
        for cam_dir in ["zoom_in", "zoom_out", "pan_right", "pan_left", "tilt_down", "tilt_up", "static"]:
            zf = zoompan_filter(1080, 1920, 3.5, scene_index=0, camera_direction=cam_dir)
            self.assertIn("zoompan=", zf)
            self.assertIn("1080x1920", zf)


if __name__ == "__main__":
    unittest.main()
