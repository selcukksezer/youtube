"""
Bölüm 33.3 P4: Sahne niyetine üç kamera hareketi testleri.
Referans: youtube-shorts-pipeline/verticals/broll.py:animate_frame
3 kamera modeli:
- Soru / Hook / Curiosity / Establishing -> zoom-in (z='1+0.12*ease')
- Geçiş / Transition / Action / Body -> pan (z='1.12', x over time)
- Kapanış / Conclusion / Outro / CTA -> zoom-out (z='1+0.12*ease_back')

Kutu kapalıyken (enable_zoompan=False): FFmpeg komutunda 'zoompan' yoktur.
Kutu açıkken (enable_zoompan=True): ardışık üç sahne üç farklı 'z=' ifadesi alır.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render.ffmpeg_graph import (
    resolve_camera_intent,
    cheap_pan_filter,
    zoompan_filter,
    build_scene_filter_chain,
    render_with_ffmpeg_graph,
)


class TestChapter33P4CameraIntent(unittest.TestCase):
    def test_resolve_camera_intent_question_mapping(self):
        """Soru ve kanca niyetleri zoom_in seçer."""
        for intent in ["question", "soru", "hook", "curiosity", "establishing", "closeup"]:
            cam = resolve_camera_intent(scene_intent=intent)
            self.assertEqual(cam, "zoom_in", f"Failed for intent: {intent}")

    def test_resolve_camera_intent_transition_mapping(self):
        """Geçiş ve gövde niyetleri pan_right seçer."""
        for intent in ["transition", "gecis", "geçiş", "action", "body", "conflict", "bridge"]:
            cam = resolve_camera_intent(scene_intent=intent)
            self.assertEqual(cam, "pan_right", f"Failed for intent: {intent}")

    def test_resolve_camera_intent_conclusion_mapping(self):
        """Kapanış ve çözüm niyetleri zoom_out seçer."""
        for intent in ["conclusion", "kapanis", "kapanış", "outro", "cta", "climax", "resolution"]:
            cam = resolve_camera_intent(scene_intent=intent)
            self.assertEqual(cam, "zoom_out", f"Failed for intent: {intent}")

    def test_resolve_camera_intent_narration_question_mark(self):
        """Anlatıda soru işareti varsa intent belirtilmemişse zoom_in seçer."""
        cam = resolve_camera_intent(narration="Bunu daha önce duymuş muydunuz?")
        self.assertEqual(cam, "zoom_in")

    def test_resolve_camera_intent_explicit_direction_takes_priority(self):
        """Açık yön (pan_left, tilt_up vb.) belirtilmişse öncelikli korunur."""
        cam = resolve_camera_intent(scene_intent="question", camera_direction="pan_left")
        self.assertEqual(cam, "pan_left")

    def test_resolve_camera_intent_sequential_three_scenes_cycle(self):
        """Niyet verilmediğinde ardışık 3 sahne sırasıyla zoom_in, pan_right, zoom_out döngüsü alır."""
        cam0 = resolve_camera_intent(scene_index=0, total_scenes=3)
        cam1 = resolve_camera_intent(scene_index=1, total_scenes=3)
        cam2 = resolve_camera_intent(scene_index=2, total_scenes=3)
        self.assertEqual(cam0, "zoom_in")
        self.assertEqual(cam1, "pan_right")
        self.assertEqual(cam2, "zoom_out")

    def test_zoompan_filter_three_distinct_z_expressions(self):
        """Kutu açıkken ardışık üç sahne üç farklı z= ifadesi alır."""
        zf0 = zoompan_filter(1080, 1920, 3.0, scene_index=0, scene_intent="question")
        zf1 = zoompan_filter(1080, 1920, 3.0, scene_index=1, scene_intent="transition")
        zf2 = zoompan_filter(1080, 1920, 3.0, scene_index=2, scene_intent="conclusion")

        self.assertIn("zoompan=", zf0)
        self.assertIn("zoompan=", zf1)
        self.assertIn("zoompan=", zf2)

        # z= ifadelerini çekelim
        def _extract_z(f_str):
            for part in f_str.split(":"):
                if part.startswith("z='") or part.startswith("zoompan=z='") or part.startswith("z="):
                    return part
            return ""

        z0 = _extract_z(zf0)
        z1 = _extract_z(zf1)
        z2 = _extract_z(zf2)

        # 1. Sahne (Soru): 1-cos (zoom_in)
        self.assertIn("1-cos", z0)
        # 2. Sahne (Geçiş): sabit zoom 1.12 (pan_right)
        self.assertIn("1.12", z1)
        self.assertNotIn("cos", z1)
        # 3. Sahne (Kapanış): 1+cos (zoom_out)
        self.assertIn("1+cos", z2)

        # Üç ifadenin tamamı birbirinden farklıdır
        self.assertNotEqual(z0, z1)
        self.assertNotEqual(z1, z2)
        self.assertNotEqual(z0, z2)

    def test_cheap_pan_filter_when_zoompan_disabled(self):
        """cheap_pan_filter asla zoompan filtresi içermez (scale+crop kullanır)."""
        cpf0 = cheap_pan_filter(1080, 1920, 3.0, scene_index=0, scene_intent="question")
        cpf1 = cheap_pan_filter(1080, 1920, 3.0, scene_index=1, scene_intent="transition")
        cpf2 = cheap_pan_filter(1080, 1920, 3.0, scene_index=2, scene_intent="conclusion")

        for f in [cpf0, cpf1, cpf2]:
            self.assertNotIn("zoompan", f)
            self.assertIn("scale=", f)
            self.assertIn("crop=", f)

    def test_build_scene_filter_chain_zoompan_flag(self):
        """build_scene_filter_chain: enable_zoompan=False iken zoompan yoktur; True iken vardır."""
        chain_no_zp = build_scene_filter_chain(
            0, 3.0, 1080, 1920, 0,
            enable_ken_burns=True,
            enable_zoompan=False,
            scene_intent="question",
        )
        self.assertNotIn("zoompan", chain_no_zp)
        self.assertIn("crop=", chain_no_zp)

        chain_with_zp = build_scene_filter_chain(
            0, 3.0, 1080, 1920, 0,
            enable_ken_burns=True,
            enable_zoompan=True,
            scene_intent="question",
        )
        self.assertIn("zoompan=", chain_with_zp)
        self.assertIn("1-cos", chain_with_zp)

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("render.ffmpeg_graph.probe_stream_color", return_value={})
    @patch("render.ffmpeg_graph._probe_duration", return_value=5.0)
    @patch("render.ffmpeg_graph._probe_is_landscape", return_value=False)
    @patch("render.ffmpeg_graph.subprocess.Popen")
    @patch("render.ffmpeg_graph.subprocess.run")
    @patch("render.ffmpeg_graph.os.path.exists")
    def test_render_with_ffmpeg_graph_zoompan_disabled_no_zoompan_in_cmd(
        self, mock_exists, mock_run, mock_popen, mock_land, mock_dur, mock_probe_col, mock_ff
    ):
        """Kutu kapalıyken (enable_zoompan=False) FFmpeg komutunda 'zoompan' yoktur."""
        mock_exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.readline.return_value = ""
        mock_proc.communicate.return_value = ("", "")
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        clips = [
            {"path": "clip1.mp4", "duration": 3.0, "scene_intent": "question"},
            {"path": "clip2.mp4", "duration": 3.0, "scene_intent": "transition"},
            {"path": "clip3.mp4", "duration": 3.0, "scene_intent": "conclusion"},
        ]

        captured_cmds = []

        def fake_popen(cmd, *args, **kwargs):
            captured_cmds.append(cmd)
            return mock_proc

        mock_popen.side_effect = fake_popen

        render_with_ffmpeg_graph(
            clips, "audio.wav", "output.mp4",
            enable_zoompan=False,
        )

        self.assertTrue(len(captured_cmds) > 0)
        called_cmd = captured_cmds[0]
        cmd_str = " ".join(called_cmd)

        self.assertIn("-filter_complex", cmd_str)
        fc_idx = called_cmd.index("-filter_complex")
        filter_complex = called_cmd[fc_idx + 1]

        # Kutu kapalıyken filter_complex içinde zoompan kesinlikle olmamalı
        self.assertNotIn("zoompan", filter_complex)

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("render.ffmpeg_graph.probe_stream_color", return_value={})
    @patch("render.ffmpeg_graph._probe_duration", return_value=5.0)
    @patch("render.ffmpeg_graph._probe_is_landscape", return_value=False)
    @patch("render.ffmpeg_graph.subprocess.Popen")
    @patch("render.ffmpeg_graph.subprocess.run")
    @patch("render.ffmpeg_graph.os.path.exists")
    def test_render_with_ffmpeg_graph_zoompan_enabled_three_scenes_three_z(
        self, mock_exists, mock_run, mock_popen, mock_land, mock_dur, mock_probe_col, mock_ff
    ):
        """Kutu açıkken (enable_zoompan=True) ardışık 3 sahne 3 farklı z= formülü alır."""
        mock_exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.readline.return_value = ""
        mock_proc.communicate.return_value = ("", "")
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        clips = [
            {"path": "clip1.mp4", "duration": 3.0, "scene_intent": "question"},
            {"path": "clip2.mp4", "duration": 3.0, "scene_intent": "transition"},
            {"path": "clip3.mp4", "duration": 3.0, "scene_intent": "conclusion"},
        ]

        captured_cmds = []

        def fake_popen(cmd, *args, **kwargs):
            captured_cmds.append(cmd)
            return mock_proc

        mock_popen.side_effect = fake_popen

        render_with_ffmpeg_graph(
            clips, "audio.wav", "output.mp4",
            enable_zoompan=True,
        )

        self.assertTrue(len(captured_cmds) > 0)
        called_cmd = captured_cmds[0]
        fc_idx = called_cmd.index("-filter_complex")
        filter_complex = called_cmd[fc_idx + 1]

        # Kutu açıkken filter_complex içinde zoompan olmalı
        self.assertIn("zoompan=", filter_complex)

        # 3 sahne için 3 zoompan filtresi olmalı
        zp_count = filter_complex.count("zoompan=")
        self.assertEqual(zp_count, 3)

        # 1. Sahne (Soru): 1-cos
        self.assertIn("1-cos", filter_complex)
        # 2. Sahne (Geçiş): z='1.12'
        self.assertIn("z='1.12'", filter_complex)
        # 3. Sahne (Kapanış): 1+cos
        self.assertIn("1+cos", filter_complex)


if __name__ == "__main__":
    unittest.main()
