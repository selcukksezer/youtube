"""
Bölüm 9.4: Otomatik Küçük Resim (Thumbnail) Sentezleyici
(Automated High-CTR Shorts Thumbnail Synthesizer)

Videonun en yüksek kontrastlı 1.5. saniyesinden otomatik kare yakalanır;
üzerine niş renginde dikkat çekici 3 kelimelik başlık yazısı basılarak
dikey kapak resmi (thumb_9x16.jpg) üretilir.

Özellikler:
- 1.5s civarındaki karelerden en yüksek kontrastlı (RMS / Standart Sapma) olanı seçme
- Başlıktan en vurucu 3 kelimelik kanca metnini çıkarma (format_3_word_hook_title)
- Nişe özel yüksek kontrastlı renk paletleri (Cyan, Gold, Neon Red, Emerald, Orange)
- Çok katmanlı gölge ve alt degrade (gradient) ile garanti okunabilirlik
- Kanonik dosya standardı: thumb_9x16.jpg (1080x1920)
"""
from __future__ import annotations

import logging
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageStat

logger = logging.getLogger(__name__)

# Standart Çözünürlükler
RES_9_16 = (1080, 1920)
RES_16_9 = (1280, 720)

# Niş Renk Paletleri (Bölüm 9.4)
NICHE_COLOR_PALETTES: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    # Finans & Kripto
    "finance": {"primary": (0, 230, 118), "accent": (0, 230, 118), "secondary": (255, 215, 0), "text": (255, 255, 255), "bg_dark": (10, 25, 15)},
    # Gizem & Korku
    "horror": {"primary": (255, 23, 68), "accent": (255, 23, 68), "secondary": (213, 0, 249), "text": (255, 255, 255), "bg_dark": (20, 5, 10)},
    # Tarih & Felsefe (Stoacılık)
    "history": {"primary": (255, 213, 79), "accent": (255, 213, 79), "secondary": (255, 179, 0), "text": (255, 255, 255), "bg_dark": (25, 20, 10)},
    # Teknoloji & Aletler
    "tech": {"primary": (0, 229, 255), "accent": (0, 229, 255), "secondary": (41, 121, 255), "text": (255, 255, 255), "bg_dark": (5, 15, 25)},
    # Sağlık & Yaşam
    "health": {"primary": (105, 240, 174), "accent": (105, 240, 174), "secondary": (0, 230, 118), "text": (255, 255, 255), "bg_dark": (10, 25, 15)},
    # E-Ticaret / Amazon Satış Ortaklığı (AFM)
    "12_amazon_affiliate": {"primary": (255, 145, 0), "accent": (255, 145, 0), "secondary": (255, 215, 0), "text": (255, 255, 255), "bg_dark": (30, 15, 5)},
    "affiliate": {"primary": (255, 145, 0), "accent": (255, 145, 0), "secondary": (255, 215, 0), "text": (255, 255, 255), "bg_dark": (30, 15, 5)},
    # Genel / Varsayılan
    "default": {"primary": (255, 215, 0), "accent": (255, 215, 0), "secondary": (0, 229, 255), "text": (255, 255, 255), "bg_dark": (15, 15, 20)},
}


def get_niche_thumbnail_palette(niche_id: str) -> Dict[str, Tuple[int, int, int]]:
    """Niş ID'sine göre en yüksek tıklama oranına (CTR) sahip renk paletini döner."""
    n_lower = str(niche_id or "").lower()
    for key, palette in NICHE_COLOR_PALETTES.items():
        if key in n_lower:
            return palette
    return NICHE_COLOR_PALETTES["default"]


def format_3_word_hook_title(title: str, niche_id: str = "general") -> str:
    """
    Bölüm 9.4: Videonun başlığından en dikkat çekici 3 kelimelik kanca metnini ayıklar.
    Gereksiz bağlaçları ve hashtag'leri temizler.
    Örnek:
    - "Bunu Neden Daha Önce Almadım Diyeceksiniz" -> "SAKIN KAÇIRMA BUNU" / "BU ÜRÜN ŞOK"
    - "Roma İmparatorluğu'nun En Gizli Sırrı" -> "GİZLİ ROMA SIRRI"
    """
    clean = re.sub(r"#\w+", "", title or "")
    clean = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ]", " ", clean)
    words = [w.strip() for w in clean.split() if w.strip()]

    # Filtrelenecek stop-words
    stop_words = {"ve", "veya", "ile", "için", "bir", "bu", "o", "şu", "gibi", "kadar", "and", "or", "the", "a", "an", "is"}
    meaningful = [w for w in words if w.lower() not in stop_words]

    if len(meaningful) >= 3:
        # İlk 3 anlamlı kelimeyi büyük harfle döndür
        return f"{meaningful[0].upper()} {meaningful[1].upper()} {meaningful[2].upper()}"
    elif len(words) >= 3:
        return f"{words[0].upper()} {words[1].upper()} {words[2].upper()}"
    elif words:
        return " ".join(w.upper() for w in words[:3])

    # Varsayılan niş kancası (ASCII safe uppercase fallback)
    n_lower = niche_id.lower()
    if "amazon" in n_lower or "affiliate" in n_lower:
        return "BU FIYATA KACMAZ"
    elif "history" in n_lower:
        return "BUYUK GIZLI TARIH"
    elif "horror" in n_lower:
        return "KORKUNC GERCEK ACIKLANDI"
    return "SOK EDICI GERCEK"


def _calculate_image_contrast(img: Image.Image) -> float:
    """Kare netliği ve kontrastını hesaplar (Standart Sapma skoru)."""
    try:
        stat = ImageStat.Stat(img.convert("L"))
        return stat.stddev[0]
    except Exception:
        return 0.0


def extract_highest_contrast_frame(
    video_path: str,
    output_path: Optional[str] = None,
    target_sec: float = 1.5,
    window_sec: float = 0.4,
) -> Optional[str]:
    """
    Bölüm 9.4: Videonun 1.5. saniyesi civarından en yüksek kontrastlı kareyi yakalar.
    Hedef: 1.5s ± 0.4s (1.1s, 1.5s, 1.9s) taranarak en net olan seçilir.
    """
    if not os.path.exists(video_path):
        return None

    actual_output = output_path or os.path.join(os.path.dirname(video_path) or ".", "_frame_1_5s.jpg")

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    timestamps = [
        max(0.2, target_sec - window_sec),
        target_sec,
        target_sec + window_sec,
    ]

    best_frame_path = None
    best_contrast = -1.0
    temp_dir = os.path.dirname(output_path) or "."

    for i, ts in enumerate(timestamps):
        candidate_path = os.path.join(temp_dir, f"_tmp_frame_{i}_{os.path.basename(output_path)}")
        cmd = [
            ffmpeg_exe,
            "-y",
            "-ss",
            f"{ts:.2f}",
            "-i",
            video_path,
            "-vframes",
            "1",
            "-q:v",
            "2",
            candidate_path,
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)
            if res.returncode == 0 and os.path.exists(candidate_path) and os.path.getsize(candidate_path) > 1000:
                with Image.open(candidate_path) as im:
                    contrast = _calculate_image_contrast(im)
                    if contrast > best_contrast:
                        best_contrast = contrast
                        if best_frame_path and os.path.exists(best_frame_path):
                            try:
                                os.remove(best_frame_path)
                            except OSError:
                                pass
                        best_frame_path = candidate_path
                    else:
                        try:
                            os.remove(candidate_path)
                        except OSError:
                            pass
        except Exception as e:
            logger.warning(f"Frame extraction at {ts}s failed: {e}")

    if best_frame_path and os.path.exists(best_frame_path):
        try:
            os.replace(best_frame_path, actual_output)
            return actual_output
        except OSError:
            pass

    # Tekil fallback (doğrudan 1.5. saniye)
    cmd = [
        ffmpeg_exe,
        "-y",
        "-ss",
        f"{target_sec:.2f}",
        "-i",
        video_path,
        "-vframes",
        "1",
        "-q:v",
        "2",
        actual_output,
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if res.returncode == 0 and os.path.exists(actual_output) and os.path.getsize(actual_output) > 1000:
            return actual_output
        return None
    except Exception:
        return None


def _find_bold_font(size: int = 84) -> ImageFont.ImageFont:
    """Sistemdeki kalın yazı tipini (Impact / Arial Bold / Segoe) yükler."""
    candidates = [
        "C:\\Windows\\Fonts\\impact.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\seguisb.ttf",
        "C:\\Windows\\Fonts\\tahomabd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def synthesize_shorts_thumbnail(
    video_path: Optional[str] = None,
    title: Optional[str] = None,
    output_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    niche_id: Optional[str] = None,
    niche: Optional[str] = None,
    timestamp_sec: float = 1.5,
    custom_hook_text: Optional[str] = None,
    hook_text: Optional[str] = None,
    dry_run: bool = False,
    **kwargs: Any,
) -> str:
    """
    Bölüm 9.4: Otomatik Küçük Resim (Thumbnail) Sentezleyici.
    Videonun 1.5. saniyesinden en yüksek kontrastlı kareyi yakalar,
    üzerine niş renginde dikkat çekici 3 kelimelik başlık basar,
    dikey kapak resmi (thumb_9x16.jpg) olarak kaydeder.
    """
    effective_niche = niche_id or niche or "general"
    effective_title = custom_hook_text or hook_text or title or "ŞOK EDİCİ GERÇEK"
    # Hedef dosya yolunu belirle
    if output_path:
        final_output = output_path
    elif output_dir:
        final_output = os.path.join(output_dir, "thumb_9x16.jpg")
    else:
        final_output = "thumb_9x16.jpg"

    os.makedirs(os.path.dirname(os.path.abspath(final_output)), exist_ok=True)
    w, h = RES_9_16

    palette = get_niche_thumbnail_palette(effective_niche)
    hook_text = (custom_hook_text or hook_text or format_3_word_hook_title(effective_title, effective_niche)).strip()

    # 1. Arka Plan Karesini Elde Et
    bg_image: Optional[Image.Image] = None
    extracted_frame = os.path.join(
        os.path.dirname(os.path.abspath(final_output)), f"_raw_frame_{timestamp_sec}.jpg"
    )

    if video_path and os.path.exists(video_path) and not dry_run:
        ok = extract_highest_contrast_frame(video_path, extracted_frame, target_sec=timestamp_sec)
        if ok and os.path.exists(extracted_frame):
            try:
                bg_image = Image.open(extracted_frame).convert("RGB")
            except Exception:
                bg_image = None
            finally:
                try:
                    os.remove(extracted_frame)
                except OSError:
                    pass

    # Fallback / Dry-run görsel oluşturma
    if bg_image is None:
        # Canlı, koyu sinematik dikey zemin
        bg_image = Image.new("RGB", (w, h), (18, 22, 36))
        d_bg = ImageDraw.Draw(bg_image)
        # Zarif arka plan şekilleri
        accent_color = palette["accent"]
        d_bg.ellipse([(-200, 300), (600, 1100)], fill=(accent_color[0] // 5, accent_color[1] // 5, accent_color[2] // 5))
        d_bg.ellipse([(400, 900), (1200, 1700)], fill=(20, 30, 50))

    # 2. 9:16 Boyutuna Hizala & Kırp
    bw, bh = bg_image.size
    scale = max(w / bw, h / bh)
    nw, nh = int(bw * scale), int(bh * scale)
    bg_image = bg_image.resize((nw, nh), Image.LANCZOS)
    x_crop = (nw - w) // 2
    y_crop = (nh - h) // 2
    bg_image = bg_image.crop((x_crop, y_crop, x_crop + w, y_crop + h))

    # 3. Kontrast İçin Alt Yarım Degrade Katmanı
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d_over = ImageDraw.Draw(overlay)
    start_y = int(h * 0.40)
    for y in range(start_y, h):
        prog = (y - start_y) / (h - start_y)
        alpha = int(prog * prog * 225)
        d_over.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    base_rgba = bg_image.convert("RGBA")
    combined = Image.alpha_composite(base_rgba, overlay).convert("RGB")
    draw = ImageDraw.Draw(combined)

    # 4. 3 Kelimelik Başlık Tipografisi (Bölüm 9.4)
    words = hook_text.split()
    font_size = 110 if len(words) <= 3 else 90
    font = _find_bold_font(font_size)

    # Kelimeleri alt alta dikey etki yaratacak şekilde yerleştir
    line_h = int(font_size * 1.25)
    start_text_y = int(h * 0.60)

    for idx, word in enumerate(words[:4]):
        y = start_text_y + (idx * line_h)
        # Niş rengi vurgusu (ilk kelime veya anahtar kelime niş rengi, diğerleri beyaz)
        if idx == 0 or idx == len(words) - 1:
            text_color = palette["accent"]
        else:
            text_color = palette["text"]

        # Metni ortala
        w_bbox = draw.textbbox((0, 0), word, font=font)
        word_w = w_bbox[2] - w_bbox[0]
        x = (w - word_w) // 2

        # 8-Yönlü 3D Drop Shadow
        shadow_dist = 6
        for dx, dy in [
            (-shadow_dist, 0),
            (shadow_dist, 0),
            (0, -shadow_dist),
            (0, shadow_dist),
            (-shadow_dist, -shadow_dist),
            (shadow_dist, shadow_dist),
            (-shadow_dist, shadow_dist),
            (shadow_dist, -shadow_dist),
        ]:
            draw.text((x + dx, y + dy), word, fill=(0, 0, 0), font=font)

        # Ön plan metni
        draw.text((x, y), word, fill=text_color, font=font)

    # 5. Kaydet (thumb_9x16.jpg)
    combined.save(final_output, "JPEG", quality=95)
    logger.info(f"Thumb_9x16 generated at: {final_output}")
    return final_output


# Geriye dönük uyumluluk takma adı
generate_thumbnail = synthesize_shorts_thumbnail
extract_best_video_frame = extract_highest_contrast_frame


class ThumbnailGenerator:
    """Sınıf tabanlı sarmalayıcı (Bölüm 9.4)."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir

    def generate(
        self,
        video_path: str,
        hook_text: str = "",
        niche: str = "general",
        output_dir: Optional[str] = None,
        dry_run: bool = False,
    ) -> str:
        dest_dir = output_dir or self.output_dir or os.path.dirname(video_path) or "output"
        return synthesize_shorts_thumbnail(
            video_path=video_path,
            hook_text=hook_text,
            niche=niche,
            output_dir=dest_dir,
            dry_run=dry_run,
        )
