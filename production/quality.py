"""Hard quality gates for research-backed Shorts packages."""
from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional


MIN_DURATION = 38.0
MAX_DURATION = 65.0
TARGET_MIN_DURATION = 45.0
TARGET_MAX_DURATION = 60.0
MAX_SCENE_DURATION = 60.0
MAX_SCENE_SEARCH_QUERIES = 8
MAX_SCENE_CLAIM_IDS = 12
MAX_SCENE_MUST_EXCLUDE = 20
MAX_SCENE_CAPTION_EMPHASIS = 12
MIN_TITLE_LENGTH = 4
MAX_TITLE_LENGTH = 100
MIN_SCENES = 6
MAX_SCENES = 12
MIN_HARD_SCENES = 4
MAX_HARD_SCENES = 24
MIN_WORDS = 85
MAX_WORDS = 195
OPTIMAL_MIN_WORDS = MIN_WORDS
OPTIMAL_MAX_WORDS = 110
MIN_SCENE_WORDS = 7
ADVISORY_SCENE_WORDS = 12
MAX_ADVISORY_SCENE_WORDS = 20


_FILLER_RE = re.compile(
    r"\b(bunu aklında tut|bunu aklinda tut|takipte kalın|takipte kalin|"
    r"yorumlarda paylaşın|yorumlarda paylasin|like atın|abone olun)\b",
    re.I,
)
_TOKEN_RE = re.compile(r"[\wçğıöşüÇĞİÖŞÜ'-]+")
_PLACEHOLDER_MARKERS = ("scene_description", "placeholder", "lorem ipsum")
_MOOD_LABEL_RE = re.compile(
    r"\*\*(?:URGENT|DRAMATIC|EPIC|CALM|MYSTERIOUS|ENERGETIC|DARK|BRIGHT|SECRET|WARNING|HOOK|CTA)\*\*\s*",
    re.I,
)
_STORY_STOPWORDS = {
    "ama", "artık", "ben", "bir", "bu", "da", "de", "diye", "en", "ile",
    "için", "ve", "the", "and", "but", "for", "with", "that", "this",
}
_NUMBER_WORD_ATOM = (
    r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|sıfır|bir|iki|"
    r"üç|dört|beş|altı|yedi|sekiz|dokuz|on|yirmi|otuz|kırk|elli|altmış|"
    r"yetmiş|seksen|doksan|yüz)"
)
_NUMBER_VALUE_PATTERN = (
    rf"(?:\d+(?:[.,]\d+)?|{_NUMBER_WORD_ATOM}"
    rf"(?:[\s-]+(?:and[\s-]+)?{_NUMBER_WORD_ATOM}){{0,3}})"
)
_NUMBER_WITH_UNIT_RE = re.compile(
    rf"\b({_NUMBER_VALUE_PATTERN})\s*(?P<unit>%|percent|yüzde|yıl|years?|gün|days?|"
    r"saat|hours?|dakika|minutes?|milyon|million|km|metres?|meters?)"
    r"(?:[ıiuü]m|[ıiuü]n|[ıiuü]|s[ıiuü]|da|de|ta|te|dan|den|tan|ten|"
    r"lık|lik|luk|lük)?\b",
    re.I,
)
_AGE_CLAIM_RE = re.compile(
    rf"\b(?P<number>{_NUMBER_VALUE_PATTERN})\s*"
    r"(?:yaş(?:ında|ındaydı|ındaydım|ındaydık|ı)?|years?\s+old|"
    r"years?\s+of\s+age|aged)\b",
    re.I,
)
_YEAR_CLAIM_RE = re.compile(r"\b((?:19|20)\d{2})\b")
_MONTH_NAME_TO_NUMBER = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12, "ocak": 1, "şubat": 2, "mart": 3,
    "nisan": 4, "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}
_MONTH_NAME_PATTERN = "|".join(
    sorted(_MONTH_NAME_TO_NUMBER, key=len, reverse=True)
)
_ISO_DATE_RE = re.compile(
    r"(?<!\d)(?P<year>(?:19|20)\d{2})-(?P<month>\d{2})-(?P<day>\d{2})(?!\d)"
)
_SLASH_ISO_DATE_RE = re.compile(
    r"(?<!\d)(?P<year>(?:19|20)\d{2})/(?P<month>\d{2})/(?P<day>\d{2})(?!\d)"
)
_DOT_DAY_FIRST_DATE_RE = re.compile(
    r"(?<!\d)(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>(?:19|20)\d{2})(?!\d)"
)
_MONTH_FIRST_DATE_RE = re.compile(
    rf"\b(?P<month>{_MONTH_NAME_PATTERN})\s+(?P<day>\d{{1,2}})"
    r"(?:st|nd|rd|th)?[,]?\s+(?P<year>(?:19|20)\d{2})\b",
    re.I,
)
_DAY_FIRST_DATE_RE = re.compile(
    rf"\b(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<month>{_MONTH_NAME_PATTERN})"
    r"\s+(?P<year>(?:19|20)\d{2})\b",
    re.I,
)
_NUMBER_WORD_VALUES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
    "sıfır": 0, "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5,
    "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10, "yirmi": 20,
    "otuz": 30, "kırk": 40, "elli": 50, "altmış": 60, "yetmiş": 70,
    "seksen": 80, "doksan": 90, "yüz": 100,
}
_CANONICAL_UNITS = {
    "%": ("percent", Decimal("1")),
    "percent": ("percent", Decimal("1")),
    "yüzde": ("percent", Decimal("1")),
    "yıl": ("time_seconds", Decimal("31536000")),
    "year": ("time_seconds", Decimal("31536000")),
    "years": ("time_seconds", Decimal("31536000")),
    "gün": ("time_seconds", Decimal("86400")),
    "day": ("time_seconds", Decimal("86400")),
    "days": ("time_seconds", Decimal("86400")),
    "saat": ("time_seconds", Decimal("3600")),
    "hour": ("time_seconds", Decimal("3600")),
    "hours": ("time_seconds", Decimal("3600")),
    "dakika": ("time_seconds", Decimal("60")),
    "minute": ("time_seconds", Decimal("60")),
    "minutes": ("time_seconds", Decimal("60")),
    "km": ("distance_meters", Decimal("1000")),
    "metre": ("distance_meters", Decimal("1")),
    "metres": ("distance_meters", Decimal("1")),
    "meter": ("distance_meters", Decimal("1")),
    "meters": ("distance_meters", Decimal("1")),
    "milyon": ("millions", Decimal("1")),
    "million": ("millions", Decimal("1")),
}
_AUDIENCE_PROMPT_RE = re.compile(
    r"\?|yorum(?:larda|lara)?|siz olsaydınız|ne düşünüyorsunuz|what would you do|comment",
    re.I,
)
_CURIOSITY_HOOK_RE = re.compile(
    r"\?|"
    r"\b(?:but|yet|how|why|what|where|who|when|hidden|secret|truth|"
    r"no one knows|nobody knows|turns out|until|except)\b|"
    r"\b(?:ama|ancak|fakat|oysa|meğer|nasıl|neden|ne oldu|ne olduğunu|"
    r"kimsenin bilmediği|gizli|sır|asıl gerçek|ta ki|tek sorun)\b",
    re.I,
)
_PREMATURE_CLOSING_RE = re.compile(
    r"^(?:in conclusion|to sum up|to summarize|in summary|that['’]s all for today|"
    r"özetle|kısacası|toparlayacak olursak|sonuç olarak|bugünlük bu kadar)\b",
    re.I,
)


def _words(value: Any) -> List[str]:
    spoken_text = _MOOD_LABEL_RE.sub("", str(value or ""))
    return _TOKEN_RE.findall(spoken_text)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _parse_number_value(raw_value: str) -> Decimal:
    raw_value = raw_value.casefold()
    try:
        return Decimal(raw_value.replace(",", "."))
    except InvalidOperation:
        tokens = re.findall(r"[a-zçğıöşü]+", raw_value)
        value = Decimal(0)
        for token in tokens:
            if token == "and":
                continue
            number = _NUMBER_WORD_VALUES[token]
            if number == 100:
                value = max(value, Decimal(1)) * 100
            else:
                value += number
        return value


def _canonical_numeric_claim(match: re.Match[str]) -> tuple[str, Decimal]:
    value = _parse_number_value(match.group(1))
    unit = match.group("unit").casefold()
    family, multiplier = _CANONICAL_UNITS.get(unit, (unit, Decimal("1")))
    return family, value * multiplier


def _extract_date_claims(text: str) -> List[tuple[int, int, date]]:
    claims = []
    for pattern in (
        _ISO_DATE_RE,
        _SLASH_ISO_DATE_RE,
        _DOT_DAY_FIRST_DATE_RE,
        _MONTH_FIRST_DATE_RE,
        _DAY_FIRST_DATE_RE,
    ):
        for match in pattern.finditer(text):
            groups = match.groupdict()
            month_value = groups["month"]
            month = (
                _MONTH_NAME_TO_NUMBER[month_value.casefold()]
                if not month_value.isdigit()
                else int(month_value)
            )
            try:
                claimed_date = date(
                    int(groups["year"]),
                    month,
                    int(groups["day"]),
                )
            except ValueError:
                continue
            claims.append((match.start(), match.end(), claimed_date))
    return sorted(claims, key=lambda claim: claim[0])


def _scene_fingerprint(scene: Dict[str, Any]) -> str:
    return _norm(" ".join([
        str(scene.get("scene_description") or ""),
        " ".join(_scene_queries(scene)[:2]),
    ]))


def _scene_queries(scene: Dict[str, Any]) -> List[str]:
    raw_queries = scene.get("search_queries")
    if not isinstance(raw_queries, list):
        return []
    return [
        query.strip()
        for query in raw_queries
        if isinstance(query, str) and query.strip()
    ]


def validate_scene_durations(
    scenes: List[Dict[str, Any]],
) -> tuple[float, List[str]]:
    """Return the finite positive scene-duration total and invalid-scene issues."""
    duration = 0.0
    issues: List[str] = []
    for index, scene in enumerate(scenes):
        raw_duration = scene.get("duration")
        try:
            scene_duration = float(raw_duration) if raw_duration is not None else 0.0
        except (TypeError, ValueError, OverflowError):
            scene_duration = 0.0
        if (
            isinstance(raw_duration, bool)
            or not math.isfinite(scene_duration)
            or scene_duration <= 0
            or scene_duration > MAX_SCENE_DURATION
        ):
            issues.append(f"scene_{index}_duration_invalid")
            continue
        duration += scene_duration
    return duration, issues


def _source_evidence_text(plan: Dict[str, Any]) -> str:
    parts: List[str] = []
    reddit_post = plan.get("reddit_post")
    if isinstance(reddit_post, dict):
        parts.extend(str(reddit_post.get(key) or "") for key in ("title", "body", "selftext"))

    snippets = plan.get("fact_snippets") or []
    if isinstance(snippets, list):
        for snippet in snippets:
            if isinstance(snippet, str):
                parts.append(snippet)
            elif isinstance(snippet, dict):
                parts.extend(
                    str(snippet.get(key) or "")
                    for key in ("title", "text", "snippet", "description", "content")
                )
    return " ".join(parts)


def _story_quality_checks(plan: Dict[str, Any], scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
    warnings: List[str] = []
    issues: List[str] = []
    title_tokens = {
        token.casefold()
        for token in _TOKEN_RE.findall(str(plan.get("title") or ""))
        if len(token) > 2 and token.casefold() not in _STORY_STOPWORDS
    }
    opening_sentence = re.split(
        r"(?<=[.!?])\s+",
        str(scenes[0].get("narration") or ""),
        maxsplit=1,
    )[0] if scenes else ""
    hook_tokens = {
        token.casefold()
        for token in _TOKEN_RE.findall(opening_sentence)
        if token.casefold() not in _STORY_STOPWORDS
    } if scenes else set()
    title_overlap = len(title_tokens & hook_tokens) / len(title_tokens) if title_tokens else 0.0
    if len(title_tokens) >= 5 and title_overlap >= 0.8:
        warnings.append(f"opening_repeats_title:{title_overlap:.2f}")

    opening_narration = " ".join(
        _MOOD_LABEL_RE.sub("", str(scene.get("narration") or "")).strip()
        for scene in scenes[:2]
    ).strip()
    opening_has_curiosity_signal = (
        bool(_CURIOSITY_HOOK_RE.search(opening_narration))
        if opening_narration else None
    )
    if opening_has_curiosity_signal is False:
        warnings.append("opening_lacks_curiosity_gap")

    repeated_pairs = []
    scene_tokens = [
        {
            token.casefold()
            for token in _TOKEN_RE.findall(str(scene.get("narration") or ""))
            if token.casefold() not in _STORY_STOPWORDS
        }
        for scene in scenes
    ]
    for left in range(len(scene_tokens)):
        for right in range(left + 1, len(scene_tokens)):
            a, b = scene_tokens[left], scene_tokens[right]
            if len(a) < 7 or len(b) < 7:
                continue
            similarity = len(a & b) / len(a | b) if (a | b) else 0.0
            if similarity >= 0.8:
                repeated_pairs.append([left, right])
    if repeated_pairs:
        warnings.append(
            "repeated_narration_scenes:"
            + ",".join(f"{left + 1}-{right + 1}" for left, right in repeated_pairs[:10])
        )

    premature_closing_scenes = [
        index + 1
        for index, scene in enumerate(scenes[:-1])
        if _PREMATURE_CLOSING_RE.match(str(scene.get("narration") or "").strip())
    ]
    if premature_closing_scenes:
        warnings.append(
            "premature_closing_tone:"
            + ",".join(f"scene_{index}" for index in premature_closing_scenes[:10])
        )

    source_text = _source_evidence_text(plan).casefold()
    source_age_matches = list(_AGE_CLAIM_RE.finditer(source_text))
    source_date_matches = _extract_date_claims(source_text)
    source_claims = {
        _canonical_numeric_claim(match)
        for match in _NUMBER_WITH_UNIT_RE.finditer(source_text)
        if not any(
            match.start() < age_match.end() and age_match.start() < match.end()
            for age_match in source_age_matches
        )
    }
    unsupported_claims = []
    conflicting_claims = []
    unsupported_ages = []
    conflicting_ages = []
    unsupported_years = []
    conflicting_years = []
    unsupported_dates = []
    conflicting_dates = []
    if source_text:
        source_age_claims = {
            _parse_number_value(match.group("number"))
            for match in source_age_matches
        }
        source_year_claims = {
            int(match.group(1))
            for match in _YEAR_CLAIM_RE.finditer(source_text)
        }
        source_date_claims = {
            claimed_date for _, _, claimed_date in source_date_matches
        }
        source_values_by_unit: Dict[str, set[str]] = {}
        for family, value in source_claims:
            source_values_by_unit.setdefault(family, set()).add(str(value))
        for index, scene in enumerate(scenes):
            narration = str(scene.get("narration") or "")
            for _, _, claimed_date in _extract_date_claims(narration):
                if claimed_date not in source_date_claims:
                    claim = f"{index + 1}:{claimed_date.isoformat()}"
                    unsupported_dates.append(claim)
                    if source_date_claims:
                        conflicting_dates.append(claim)

            age_matches = list(_AGE_CLAIM_RE.finditer(narration))
            for match in age_matches:
                age = _parse_number_value(match.group("number"))
                if age not in source_age_claims:
                    claim = f"{index + 1}:{match.group('number')}years"
                    unsupported_ages.append(claim)
                    if source_age_claims:
                        conflicting_ages.append(claim)

            for match in _YEAR_CLAIM_RE.finditer(narration):
                year = int(match.group(1))
                if year not in source_year_claims:
                    claim = f"{index + 1}:{year}"
                    unsupported_years.append(claim)
                    if source_year_claims:
                        conflicting_years.append(claim)

            for match in _NUMBER_WITH_UNIT_RE.finditer(narration):
                if any(
                    match.start() < age_match.end() and age_match.start() < match.end()
                    for age_match in age_matches
                ):
                    continue
                family, canonical_value = _canonical_numeric_claim(match)
                raw_value = match.group(1).replace(",", ".")
                raw_unit = match.group("unit").casefold()
                claim = f"{index + 1}:{raw_value}{raw_unit}"
                if (family, canonical_value) not in source_claims:
                    unsupported_claims.append(claim)
                    if source_values_by_unit.get(family):
                        conflicting_claims.append(claim)
        if unsupported_claims:
            warnings.append("numeric_claims_not_in_source:" + ",".join(unsupported_claims[:10]))
        if conflicting_claims:
            conflict_detail = ",".join(conflicting_claims[:10])
            warnings.append("numeric_source_conflicts:" + conflict_detail)
            issues.append("numeric_source_conflicts:" + conflict_detail)
        if unsupported_ages:
            warnings.append("age_claims_not_in_source:" + ",".join(unsupported_ages[:10]))
        if conflicting_ages:
            conflict_detail = ",".join(conflicting_ages[:10])
            warnings.append("age_source_conflicts:" + conflict_detail)
            issues.append("age_source_conflicts:" + conflict_detail)
        if unsupported_years:
            warnings.append("year_claims_not_in_source:" + ",".join(unsupported_years[:10]))
        if conflicting_years:
            conflict_detail = ",".join(conflicting_years[:10])
            warnings.append("year_source_conflicts:" + conflict_detail)
            issues.append("year_source_conflicts:" + conflict_detail)
        if unsupported_dates:
            warnings.append("date_claims_not_in_source:" + ",".join(unsupported_dates[:10]))
        if conflicting_dates:
            conflict_detail = ",".join(conflicting_dates[:10])
            warnings.append("date_source_conflicts:" + conflict_detail)
            issues.append("date_source_conflicts:" + conflict_detail)

    final_narration = str(scenes[-1].get("narration") or "").strip() if scenes else ""
    has_viewer_prompt = bool(_AUDIENCE_PROMPT_RE.search(final_narration))
    ending_style = "viewer_prompt" if has_viewer_prompt else "statement" if final_narration else "missing"
    if ending_style == "missing":
        warnings.append("ending_scene_missing")
    elif ending_style == "statement" and len(_words(final_narration)) < ADVISORY_SCENE_WORDS:
        warnings.append("ending_is_brief_statement")

    return {
        "issues": issues,
        "warnings": warnings,
        "opening_title_overlap": round(title_overlap, 3),
        "opening_has_curiosity_signal": opening_has_curiosity_signal,
        "repeated_narration_pairs": repeated_pairs[:10],
        "premature_closing_scenes": premature_closing_scenes[:10],
        "numeric_source_check": (
            "numeric, age, year, and date claims only"
            if source_text else "source text unavailable"
        ),
        "ending_style": ending_style,
    }


def validate_script_quality(plan: Dict[str, Any], *, channel_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a deterministic report; never silently upgrades a weak script."""
    plan = plan or {}
    raw_scenes = plan.get("scenes")
    scenes = (
        [scene for scene in raw_scenes if isinstance(scene, dict)]
        if isinstance(raw_scenes, list)
        else []
    )
    scenes_invalid = raw_scenes is not None and (
        not isinstance(raw_scenes, list) or len(scenes) != len(raw_scenes)
    )
    scene_narration = " ".join(
        value for s in scenes
        if isinstance((value := s.get("narration")), str)
    )
    full_narration = str(plan.get("full_narration") or "")
    scene_words = _words(scene_narration)
    full_words = _words(full_narration)
    words = scene_words if scenes else full_words
    issues: List[str] = []
    warnings: List[str] = []

    title = plan.get("title")
    if not isinstance(title, str):
        issues.append("title_invalid")
    else:
        title_length = len(title.strip())
        if not MIN_TITLE_LENGTH <= title_length <= MAX_TITLE_LENGTH:
            issues.append(f"title_length_out_of_bounds:{title_length}")

    if scenes_invalid:
        issues.append("scenes_invalid")

    duration, duration_issues = validate_scene_durations(scenes)
    issues.extend(duration_issues)

    if scenes and full_narration and full_words != scene_words:
        issues.append("full_narration_mismatch")

    # Duration hard band is wider than the 45-60s production target.
    if duration < MIN_DURATION or duration > MAX_DURATION:
        issues.append(f"duration_out_of_band:{duration:.2f}")
    elif not (TARGET_MIN_DURATION <= duration <= TARGET_MAX_DURATION + 0.25):
        warnings.append(f"duration_near_band_edge:{duration:.2f}")

    if len(scenes) < MIN_HARD_SCENES:
        issues.append(f"scene_count_out_of_band:{len(scenes)}")
    elif len(scenes) > MAX_HARD_SCENES:
        issues.append(f"scene_count_exceeds_limit:{len(scenes)}")
    elif not (MIN_SCENES <= len(scenes) <= MAX_SCENES):
        warnings.append(f"scene_count_near_edge:{len(scenes)}")

    # Word count: 85-195 is hard band; the natural TTS target is 85-110.
    if not (MIN_WORDS <= len(words) <= MAX_WORDS):
        issues.append(f"word_count_out_of_band:{len(words)}")
    elif len(words) < OPTIMAL_MIN_WORDS:
        warnings.append(f"word_count_below_optimal:{len(words)}_target_{OPTIMAL_MIN_WORDS}")
    elif len(words) > OPTIMAL_MAX_WORDS:
        warnings.append(f"word_count_above_optimal:{len(words)}_target_{OPTIMAL_MAX_WORDS}")

    if not scenes:
        issues.append("scenes_missing")

    fingerprints = [_scene_fingerprint(s) for s in scenes]
    repeated = [key for key, count in Counter(fingerprints).items() if key and count > 1]
    if repeated:
        warnings.append(f"repeated_scene_fingerprint:{len(repeated)}")

    for index, scene in enumerate(scenes):
        raw_narration = scene.get("narration")
        narration = raw_narration.strip() if isinstance(raw_narration, str) else ""
        if not isinstance(raw_narration, str):
            issues.append(f"scene_{index}_narration_invalid")
        elif any(marker in narration.casefold() for marker in _PLACEHOLDER_MARKERS):
            issues.append(f"scene_{index}_narration_placeholder")
        raw_description = scene.get("scene_description")
        description = raw_description.strip() if isinstance(raw_description, str) else ""
        queries = _scene_queries(scene)
        raw_queries = scene.get("search_queries")
        w_count = len(_words(narration))
        visual_intent = scene.get("visual_intent")
        if w_count < MIN_SCENE_WORDS:
            issues.append(f"scene_{index}_words_below_{MIN_SCENE_WORDS}")
        elif w_count < ADVISORY_SCENE_WORDS:
            warnings.append(f"scene_{index}_words_below_{ADVISORY_SCENE_WORDS}")
        elif w_count > MAX_ADVISORY_SCENE_WORDS:
            warnings.append(f"scene_{index}_words_above_{MAX_ADVISORY_SCENE_WORDS}")
        if (
            not description
            or len(description) < 12
            or any(marker in description.casefold() for marker in _PLACEHOLDER_MARKERS)
        ):
            issues.append(f"scene_{index}_visual_description_invalid")
        if raw_queries is not None and (
            not isinstance(raw_queries, list)
            or any(not isinstance(query, str) for query in raw_queries)
        ):
            issues.append(f"scene_{index}_queries_invalid")
        if len(queries) < 2:
            issues.append(f"scene_{index}_queries_insufficient")
        if isinstance(raw_queries, list) and len(raw_queries) > MAX_SCENE_SEARCH_QUERIES:
            issues.append(
                f"scene_{index}_queries_above_{MAX_SCENE_SEARCH_QUERIES}"
            )
        for field, maximum in (
            ("claim_ids", MAX_SCENE_CLAIM_IDS),
            ("must_exclude", MAX_SCENE_MUST_EXCLUDE),
            ("caption_emphasis", MAX_SCENE_CAPTION_EMPHASIS),
        ):
            if field not in scene:
                continue
            values = scene[field]
            if not isinstance(values, list) or any(
                not isinstance(value, str) for value in values
            ):
                issues.append(f"scene_{index}_{field}_invalid")
            elif len(values) > maximum:
                issues.append(f"scene_{index}_{field}_above_{maximum}")
        if visual_intent is not None and not isinstance(visual_intent, dict):
            issues.append(f"scene_{index}_visual_intent_invalid")
        if _FILLER_RE.search(narration):
            warnings.append(f"scene_{index}_mechanical_filler")
        if narration and narration[-1] not in ".!?":
            warnings.append(f"scene_{index}_missing_terminal")

    if len(words) < OPTIMAL_MIN_WORDS:
        warnings.append("regenerate_with_deeper_argument")
    if len(words) > OPTIMAL_MAX_WORDS:
        warnings.append("condense_by_removing_redundancy_not_generic_padding")
    if duration < 50:
        warnings.append("shorter_than_viewmade_style_default")

    story_quality = _story_quality_checks(plan, scenes)
    issues.extend(story_quality["issues"])
    warnings.extend(story_quality["warnings"])

    hard = bool(issues)
    return {
        "ok": not hard,
        "action": "DROP" if hard else "RENDER_ALLOWED",
        "hard_fail": hard,
        "issues": issues,
        "warnings": warnings,
        "story_quality": story_quality,
        "duration": round(duration, 3),
        "scene_count": len(scenes),
        "word_count": len(words),
        "limits": {
            "min_duration": MIN_DURATION,
            "max_duration": MAX_DURATION,
            "target_min_duration": TARGET_MIN_DURATION,
            "target_max_duration": TARGET_MAX_DURATION,
            "max_scene_duration": MAX_SCENE_DURATION,
            "min_scenes": MIN_SCENES,
            "max_scenes": MAX_SCENES,
            "hard_min_scenes": MIN_HARD_SCENES,
            "hard_max_scenes": MAX_HARD_SCENES,
            "max_scene_claim_ids": MAX_SCENE_CLAIM_IDS,
            "max_scene_must_exclude": MAX_SCENE_MUST_EXCLUDE,
            "max_scene_caption_emphasis": MAX_SCENE_CAPTION_EMPHASIS,
            "min_title_length": MIN_TITLE_LENGTH,
            "max_title_length": MAX_TITLE_LENGTH,
            "min_words": MIN_WORDS,
            "max_words": MAX_WORDS,
            "min_scene_words": MIN_SCENE_WORDS,
            "max_advisory_scene_words": MAX_ADVISORY_SCENE_WORDS,
            "max_scene_search_queries": MAX_SCENE_SEARCH_QUERIES,
        },
        "channel_profile": channel_profile or {},
    }


def build_policy_snapshot(*, ai_disclosure_required: bool = False, sources: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Record policy inputs without pretending that a URL fetch is legal proof."""
    from datetime import datetime, timezone

    urls = list(sources or [
        "https://support.google.com/youtube/answer/1311392",
        "https://support.google.com/youtube/answer/12504220",
        "https://support.google.com/youtube/answer/14328491",
        "https://support.google.com/youtube/answer/6162278",
        "https://support.google.com/youtube/answer/2801973",
        "https://support.google.com/youtube/answer/2797370",
    ])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_urls": urls,
        "source_confidence": "official_urls_snapshot_recheck_before_publish",
        "ai_disclosure_required": bool(ai_disclosure_required),
        "manual_recheck_required": True,
        "rules": {
            "no_mass_produced_repetitive_templates": True,
            "no_reuploads_or_fake_engagement": True,
            "license_manifest_required": True,
            "factual_claims_need_independent_evidence": True,
        },
    }
