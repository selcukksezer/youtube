"""Content-ID risk heuristics for selected visual and audio sources."""
import re


_KNOWN_CONTENTID_PATTERNS = [
    r"epidemic[\s_-]?sound", r"artlist", r"musicbed", r"soundstripe", r"pond5[\s_-]?music",
    r"premiumbeat", r"audiojungle", r"story[\s_-]?blocks", r"shutterstock[\s_-]?editorial",
    r"getty[\s_-]?images", r"getty[\s_-]?video", r"ap[\s_-]?archive", r"reuters[\s_-]?video",
    r"bbc[\s_-]?motion", r"nbc[\s_-]?universal", r"fox[\s_-]?news", r"cnn[\s_-]?footage",
    r"movie[\s_-]?clip", r"film[\s_-]?scene", r"trailer[\s_-]?official", r"epic[\s_-]?cinematic",
    r"hans[\s_-]?zimmer", r"disney[\s_-]?soundtrack", r"warner[\s_-]?music", r"sony[\s_-]?music",
    r"universal[\s_-]?music",
]
_COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in _KNOWN_CONTENTID_PATTERNS]
_SAFE_SOURCES = {
    "pexels", "pixabay", "unsplash", "coverr", "mixkit", "videvo", "freepik_video", "ai_generated",
    "custom_footage", "openverse", "youtube_audio_library_free", "ccmixter", "freemusicarchive",
    "bensound_free", "incompetech", "purple_planet",
}


def scan_copyright_risk(clip_names: list, source_labels: list = None) -> dict:
    """Classifies known Content-ID or suspicious source-name patterns."""
    flagged, safe_clips, recommendations = [], [], []
    all_items = list(clip_names or []) + list(source_labels or [])
    for item in all_items:
        item_str = str(item).lower()
        if any(source in item_str for source in _SAFE_SOURCES):
            safe_clips.append(item)
            continue
        matched_pattern = next((pattern.pattern for pattern in _COMPILED_PATTERNS if pattern.search(item_str)), None)
        if matched_pattern:
            flagged.append({"item": item, "matched_pattern": matched_pattern, "risk": "high"})
            recommendations.append(f"'{item}' → Pexels/Pixabay/AI üretimi ile değiştirin (eşleşen kalıp: {matched_pattern})")
        elif any(keyword in item_str for keyword in ("official", "hd_download", "full_movie", "episode", "season")):
            flagged.append({"item": item, "matched_pattern": "suspicious_keyword", "risk": "medium"})
            recommendations.append(f"'{item}' → Kaynak lisansını doğrulayın veya alternatif kullanın.")
        else:
            safe_clips.append(item)
    risk_level = "high" if any(item["risk"] == "high" for item in flagged) else "medium" if flagged else "low"
    return {"safe": not flagged, "risk_level": risk_level, "flagged_items": flagged, "safe_items": safe_clips, "recommendations": recommendations}


def scan_audio_copyright_risk(track_names: list) -> dict:
    """Item 190: Audio fingerprint / Content-ID heuristics for BGM track filenames."""
    flagged, safe_tracks, recommendations = [], [], []
    for item in track_names or []:
        item_str = str(item).lower()
        if any(source in item_str for source in _SAFE_SOURCES):
            safe_tracks.append(item)
            continue
        matched = next((p.pattern for p in _COMPILED_PATTERNS if p.search(item_str)), None)
        if matched:
            flagged.append({"item": item, "matched_pattern": matched, "risk": "high"})
            recommendations.append(
                f"'{item}' → YouTube Audio Library / royalty_free_ambient ile değiştirin ({matched})"
            )
        elif any(k in item_str for k in ("official", "remix", "cover", "soundtrack", "ost")):
            flagged.append({"item": item, "matched_pattern": "suspicious_audio_keyword", "risk": "medium"})
            recommendations.append(f"'{item}' → Telifsiz katalogdan doğrulanmış parça seçin.")
        else:
            safe_tracks.append(item)
    risk_level = "high" if any(i["risk"] == "high" for i in flagged) else "medium" if flagged else "low"
    return {
        "safe": not flagged,
        "risk_level": risk_level,
        "flagged_items": flagged,
        "safe_items": safe_tracks,
        "recommendations": recommendations,
    }


def scenes_need_fair_use_enforcement(scenes: list) -> bool:
    """Item 96: True when any scene search query matches copyright-risk patterns."""
    queries = []
    for sc in scenes or []:
        queries.extend(sc.get("search_queries") or [])
        if sc.get("is_copyrighted"):
            return True
    scan = scan_copyright_risk(queries)
    return not scan.get("safe", True)


def filter_safe_clips(clip_names: list, source_labels: list = None, abort_on_high_risk: bool = False) -> list:
    """Removes items flagged by ``scan_copyright_risk``."""
    scan = scan_copyright_risk(clip_names, source_labels)
    if abort_on_high_risk and scan["risk_level"] == "high":
        raise ValueError(f"[Item 110] Yüksek telif riski tespit edildi! Riskli öğeler: {[item['item'] for item in scan['flagged_items']]}")
    flagged_items = {item["item"] for item in scan["flagged_items"]}
    return [clip for clip in clip_names if clip not in flagged_items]