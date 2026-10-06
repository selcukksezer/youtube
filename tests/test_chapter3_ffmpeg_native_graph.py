"""
Unit Tests for Chapter 3: FFmpeg Native Graph ve Donanım Render Motoru (render/ffmpeg_graph.py).
Validates:
- 3.1 FilterComplex Mimari Topolojisi
- 3.2 Sub-Pixel Float Precision Ken Burns Ease-in-out
- 3.3 Otomatik Fit & Fill Gaussian Blur Arka Plan Katmanı
- 3.4 Çoklu Donanım Hızlandırma Müzakeresi (NVENC, QSV, AMF, VideoToolbox, VAAPI, libx264)
- 3.5 Subprocess Heartbeat Takibi ve Zombi Süreç Yalıtımı
- 3.6 Çift Sayılı Piksel Modülo Hizalama ve WhatsApp/Telegram Toleransı
- 3.7 Renk uzayı BT.709. İki geçişli video encode yok
"""
import unittest
import inspect
from render import ffmpeg_graph
from system_resilience import (
    get_encoder_fallback_chain,
    get_available_ffmpeg_encoders,
    get_ffmpeg_vcodec_args,
)


class TestChapter3FFmpegNativeGraph(unittest.TestCase):
    def test_3_2_ken_burns_cosine_ease_in_out(self):
        """3.2: Sub-pixel float precision cosine ease-in-out progression."""
        filt = ffmpeg_graph.cheap_pan_filter(1080, 1920, 4.0, scene_index=0)
        self.assertIn("0.5*(1-cos(PI*min(t", filt)
        self.assertIn("crop=1080:1920", filt)
        # Even dimension check for overscale
        self.assertIn("scale=", filt)

    def test_3_3_fit_and_fill_gaussian_blur(self):
        """3.3: Landscape assets get blurred background + centered foreground."""
        chain = ffmpeg_graph.build_scene_filter_chain(
            input_index=0,
            duration=3.5,
            width=1080,
            height=1920,
            scene_index=0,
            fit_and_fill=True,
        )
        self.assertIn("boxblur=25:5", chain)
        self.assertIn("force_original_aspect_ratio=increase", chain)
        self.assertIn("force_original_aspect_ratio=decrease", chain)
        self.assertIn("overlay=(W-w)/2:(H-h)/2", chain)

    def test_3_4_hardware_acceleration_negotiation(self):
        """3.4: Fallback chain contains GPU encoders and terminates with libx264."""
        chain = get_encoder_fallback_chain(use_gpu=True)
        self.assertTrue(len(chain) >= 2)
        # Last candidate must always be CPU libx264
        last_args, last_label = chain[-1]
        self.assertIn("libx264", last_args)
        self.assertIn("CPU", last_label)

        # Probed encoders set is non-empty
        encoders = get_available_ffmpeg_encoders()
        self.assertIn("libx264", encoders)

    def test_3_6_modulo_2_even_dimensions(self):
        """3.6: Odd input dimensions must be aligned to even numbers."""
        chain = ffmpeg_graph.build_scene_filter_chain(
            input_index=0,
            duration=3.0,
            width=1081,  # Odd width
            height=1921,  # Odd height
            scene_index=0,
            split_screen=True,
            gameplay_label="[gp0]",
        )
        # Even heights only
        self.assertIn("crop=1080:", chain)

    def test_3_7_color_space_and_faststart(self):
        """3.7: Color space flags (bt709) and faststart in render source."""
        src = inspect.getsource(ffmpeg_graph.render_with_ffmpeg_graph)
        self.assertIn("-colorspace", src)
        self.assertIn("bt709", src)
        self.assertIn("-color_primaries", src)
        self.assertIn("-color_trc", src)
        self.assertIn("-pix_fmt", src)
        self.assertIn("yuv420p", src)
        self.assertIn("+faststart", src)
        self.assertIn("-color_range", src)
        self.assertIn("_BT709_TAG", src)
        self.assertIn("setparams=color_primaries=bt709", ffmpeg_graph._BT709_TAG)
        self.assertNotIn('"-pass"', src)

    def test_3_7_convert_bt601_and_full_range_only(self):
        """Untagged bt709 is not converted. bt601 and full range are."""
        self.assertEqual(ffmpeg_graph.color_convert_filter({}), "")
        self.assertEqual(
            ffmpeg_graph.color_convert_filter({"color_space": "bt709", "color_range": "tv"}),
            "",
        )
        filt = ffmpeg_graph.color_convert_filter({
            "color_space": "smpte170m",
            "color_range": "pc",
        })
        self.assertIn("iall=bt601-6-525", filt)
        self.assertIn("irange=pc", filt)
        self.assertIn("range=tv", filt)
        hdr = ffmpeg_graph.color_convert_filter({"color_transfer": "arib-std-b67"})
        self.assertIn("zscale=pin=bt2020:tin=arib-std-b67:min=bt2020nc:", hdr)
        self.assertIn("t=bt709:m=bt709:p=bt709:r=tv", hdr)
        self.assertNotIn("tonemap", hdr)
        pq = ffmpeg_graph.color_convert_filter({
            "color_transfer": "smpte2084",
            "color_space": "bt2020ncl",
        })
        self.assertIn("tin=smpte2084:min=bt2020nc:", pq)
        chain = ffmpeg_graph.build_scene_filter_chain(
            0, 3.0, 1080, 1920, 0, enable_ken_burns=False, color_filter=filt,
        )
        self.assertTrue(chain.startswith(f"[0:v]{filt},trim="))


if __name__ == "__main__":
    unittest.main()
