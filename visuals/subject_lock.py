"""Concrete shot lock.

A sentence about a skyscraper must search for a skyscraper.
Niche mood banks (ocean, marble, fog) are not a substitute when the
sentence names something a camera can film.

ViewMade's researched-short path works the same way: read the scene,
then fetch real footage of that subject and reframe it. License checks
stay in the providers. This module only decides the search subject.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence


_FOLD = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
    "â": "a", "î": "i", "û": "u",
})


def fold(text: str) -> str:
    return (text or "").casefold().translate(_FOLD)


def _has_phrase(folded: str, needle: str) -> bool:
    n = fold(needle).strip()
    if len(n) < 3:
        return False
    if " " in n:
        return n in folded
    # Long stems keep Turkish suffixes: gökdelen / gökdelenlerin / gökdeleni.
    # Short stems stay whole words so "kale" does not hit "kalem".
    if len(n) >= 6:
        return re.search(rf"(?<![a-z0-9]){re.escape(n)}", folded) is not None
    return re.search(rf"(?<![a-z0-9]){re.escape(n)}(?![a-z0-9])", folded) is not None


@dataclass(frozen=True)
class ShotFamily:
    root: str
    primary: str
    variants: tuple
    needles: tuple


# Longest needle wins. Variants stay inside the same real-world subject
# so a split scene does not jump from a tower to a random beach.
FAMILIES: tuple = (
    ShotFamily(
        "skyscraper",
        "skyscraper tower city",
        ("skyscraper glass facade", "skyscraper construction crane", "city skyline skyscrapers aerial", "skyscraper elevator interior"),
        ("gokdelen", "skyscraper", "high rise", "highrise", "burj khalifa", "empire state", "gokdelenler"),
    ),
    ShotFamily(
        "bridge",
        "bridge structure over water",
        ("suspension bridge cables", "bridge traffic aerial", "bridge at night lights"),
        ("kopru", "bridge", "bogaz koprusu", "suspension bridge"),
    ),
    ShotFamily(
        "mosque",
        "mosque dome",
        ("minaret dawn", "mosque interior", "open quran book", "muslim prayer hands"),
        ("cami", "camii", "kubbe", "minare", "mosque", "kuran", "quran", "namaz", "mescid"),
    ),
    ShotFamily(
        "church",
        "cathedral interior",
        ("church stained glass", "cathedral exterior", "church candles"),
        ("katedral", "kilise", "cathedral", "stained glass"),
    ),
    ShotFamily(
        "bitcoin",
        "bitcoin coin close up",
        ("cryptocurrency trading chart", "trading desk monitors", "stock market ticker"),
        ("bitcoin", "kripto", "blockchain", "borsa", "hisse senedi", "candlestick"),
    ),
    ShotFamily(
        "rome",
        "roman marble bust",
        ("roman marble columns", "ancient parchment closeup", "roman forum ruins", "olive tree wind"),
        ("marcus aurelius", "marcus", "stoaci", "stoacilik", "stoic", "seneca", "epiktet", "colosseum", "kolezyum", "roma forumu"),
    ),
    ShotFamily(
        "pyramid",
        "egyptian pyramids desert",
        ("ancient egypt temple", "sphinx close up", "hieroglyph wall"),
        ("piramit", "pyramid", "misir", "egypt", "sfinks", "sphinx", "hiyeroglif"),
    ),
    ShotFamily(
        "war",
        "historical battlefield",
        ("old war documentary film", "soldiers marching archive", "military map table"),
        ("savas", "battlefield", "ordusu", "kusatma", "tank", "dunya savasi"),
    ),
    ShotFamily(
        "space",
        "earth from space",
        ("rocket launch", "astronaut spacewalk", "galaxy stars", "moon surface"),
        ("uzay", "astronot", "roket", "galaksi", "karadelik", "black hole", "nasa", "james webb", "uydusu", "gezegen"),
    ),
    ShotFamily(
        "ocean",
        "ocean waves",
        ("underwater deep sea", "whale underwater", "coral reef fish", "ship deck storm"),
        ("okyanus", "deniz alti", "balina", "mercan", "gemi", "firtina denizi", "deep sea"),
    ),
    ShotFamily(
        "forest",
        "forest path trees",
        ("jungle canopy", "moss forest close up", "woodland fog"),
        ("orman", "jungle", "yagmur ormani", "agaclar"),
    ),
    ShotFamily(
        "desert",
        "desert dunes",
        ("desert caravan", "sandstorm desert", "canyon rocks"),
        ("col", "desert", "kumul", "sahara"),
    ),
    ShotFamily(
        "volcano",
        "volcano eruption lava",
        ("lava flow close up", "volcano smoke crater"),
        ("volkan", "volcano", "lav", "lava"),
    ),
    ShotFamily(
        "glacier",
        "glacier ice cliff",
        ("arctic ice ocean", "penguin colony ice", "iceberg aerial"),
        ("buzul", "glacier", "antarktika", "kutup", "penguen", "iceberg", "arktik"),
    ),
    ShotFamily(
        "animal_cat",
        "cat close up",
        ("kitten playing", "cat walking indoor"),
        ("kedi", "kitten", "cat "),
    ),
    ShotFamily(
        "animal_dog",
        "dog close up",
        ("puppy running", "dog portrait outdoor"),
        ("kopek", "puppy", "dog "),
    ),
    ShotFamily(
        "lion",
        "lion wildlife close up",
        ("lion walking savanna", "lioness hunting grass"),
        ("aslan", "lion"),
    ),
    ShotFamily(
        "shark",
        "shark underwater",
        ("great white shark", "shark swimming ocean"),
        ("kopekbaligi", "shark"),
    ),
    ShotFamily(
        "snake",
        "snake close up",
        ("snake in grass", "cobra hood"),
        ("yilan", "snake", "kobra"),
    ),
    ShotFamily(
        "eagle",
        "eagle flying",
        ("bird of prey soaring", "eagle close up feathers"),
        ("kartal", "eagle"),
    ),
    ShotFamily(
        "brain",
        "human brain scan",
        ("neuron microscope", "mri brain scan", "psychology silhouette thinking"),
        ("beyin", "neuron", "noron", "mri"),
    ),
    ShotFamily(
        "heart",
        "human heart medical",
        ("ecg monitor hospital", "doctor stethoscope"),
        ("kalp", "ekg", "stetoskop"),
    ),
    ShotFamily(
        "microscope",
        "microscope laboratory",
        ("laboratory glassware", "scientist lab coat"),
        ("mikroskop", "laboratuvar", "microscope", "deney"),
    ),
    ShotFamily(
        "train",
        "train railway motion",
        ("subway train station", "steam train vintage"),
        ("tren", "metro", "railway", "istasyon"),
    ),
    ShotFamily(
        "plane",
        "airplane takeoff",
        ("airplane window clouds", "airport runway", "jet cockpit"),
        ("ucak", "airplane", "havalimani", "pilot"),
    ),
    ShotFamily(
        "ship",
        "cargo ship ocean",
        ("sailboat sea", "port cranes containers"),
        ("gemi", "yelkenli", "liman", "cargo ship"),
    ),
    ShotFamily(
        "car",
        "sports car driving",
        ("car engine close up", "night city driving", "supercar detail"),
        ("ferrari", "lamborghini", "supercar", "hypercar", "spor araba", "otomobil"),
    ),
    ShotFamily(
        "phone",
        "smartphone in hands",
        ("phone screen close up", "typing on phone night"),
        ("telefon", "smartphone", "whatsapp", "ekran"),
    ),
    ShotFamily(
        "book",
        "old book pages",
        ("library shelves", "hand writing notebook"),
        ("kitap", "kutuhane", "kutuphane", "parchment", "elyazmasi"),
    ),
    ShotFamily(
        "money",
        "cash bills close up",
        ("coins macro", "bank vault", "wallet money"),
        ("banknot", "nakit", "kasa", "cash"),
    ),
    ShotFamily(
        "factory",
        "factory machines",
        ("assembly line workers", "industrial sparks welding"),
        ("fabrika", "factory", "montaj hatti", "kaynak makinesi"),
    ),
    ShotFamily(
        "kitchen",
        "kitchen cooking hands",
        ("chef flame pan", "food close up"),
        ("mutfak", "asci", "yemek pisirme", "tavada"),
    ),
    ShotFamily(
        "coffee",
        "coffee pouring cup",
        ("espresso machine", "coffee beans macro"),
        ("kahve", "espresso", "coffee"),
    ),
    ShotFamily(
        "gym",
        "gym workout",
        ("runner on road", "barbell close up"),
        ("fitness", "spor salonu", "halter", "kosu", "gym"),
    ),
    ShotFamily(
        "football",
        "football stadium night",
        ("soccer ball kick", "football crowd"),
        ("futbol", "stadyum", "soccer", "premier league"),
    ),
    ShotFamily(
        "basketball",
        "basketball court",
        ("basketball dunk", "basketball close up"),
        ("basketbol", "basketball"),
    ),
    ShotFamily(
        "chess",
        "chess board close up",
        ("chess pieces macro", "person thinking chess"),
        ("satranc", "chess"),
    ),
    ShotFamily(
        "fire",
        "fire flames close up",
        ("campfire night", "burning building"),
        ("yangin", "alev", "campfire", "ates"),
    ),
    ShotFamily(
        "rain",
        "rain on window",
        ("rain city street", "storm lightning"),
        ("yagmur", "simsek", "lightning", "firtina"),
    ),
    ShotFamily(
        "snow",
        "snow falling street",
        ("snow mountains", "ski slope"),
        ("kar yagisi", "kayak", "snow"),
    ),
    ShotFamily(
        "map",
        "old map close up",
        ("world map wall", "compass on map"),
        ("harita", "world map", "pusula"),
    ),
    ShotFamily(
        "castle",
        "medieval castle",
        ("castle walls", "knight armor museum"),
        ("kale", "sovalye", "castle", "zirh"),
    ),
    ShotFamily(
        "court",
        "courtroom interior",
        ("judge gavel", "law books shelf"),
        ("mahkeme", "hakim", "courtroom", "gavel"),
    ),
    ShotFamily(
        "hospital",
        "hospital corridor",
        ("surgery lights", "ambulance night"),
        ("hastane", "ambulans", "ameliyat", "hospital"),
    ),
    ShotFamily(
        "school",
        "classroom chalkboard",
        ("students classroom", "library study desk"),
        ("sinif", "okul", "tahta", "classroom"),
    ),
    ShotFamily(
        "server",
        "server room lights",
        ("data center aisle", "computer code screen"),
        ("sunucu", "server room", "data center", "yazilim kodu"),
    ),
    ShotFamily(
        "robot",
        "robot arm factory",
        ("humanoid robot", "circuit board macro"),
        ("robot", "devre karti", "yapay zeka robot"),
    ),
    ShotFamily(
        "telescope",
        "telescope observatory",
        ("night sky milky way", "astronomer telescope"),
        ("teleskop", "gozlemevi", "samanyolu", "telescope"),
    ),
    ShotFamily(
        "flower",
        "flower macro",
        ("garden flowers", "bee on flower"),
        ("cicek", "flower", "ari"),
    ),
    ShotFamily(
        "mountain",
        "mountain peak aerial",
        ("hiker mountain trail", "snow mountain ridge"),
        ("dag zirvesi", "mountain", "zirve"),
    ),
    ShotFamily(
        "waterfall",
        "waterfall forest",
        ("waterfall close up", "river rapids"),
        ("selale", "waterfall", "caglayan"),
    ),
    ShotFamily(
        "cave",
        "cave interior light",
        ("stalactite cave", "dark tunnel"),
        ("magara", "cave"),
    ),
    ShotFamily(
        "subway",
        "subway train underground",
        ("metro platform people", "underground tunnel train"),
        ("metro istasyonu", "subway"),
    ),
    ShotFamily(
        "clock",
        "clock close up",
        ("pocket watch macro", "clock gears"),
        ("saat mekanizmasi", "cep saati", "clock gears", "hourglass", "kum saati"),
    ),
    ShotFamily(
        "dna",
        "dna helix model",
        ("genetics laboratory", "microscope cells"),
        ("dna", "genetik", "kromozom"),
    ),
    ShotFamily(
        "atom",
        "atom science abstract",
        ("particle physics laboratory", "nuclear power plant exterior"),
        ("atom", "nukleer", "parcacik"),
    ),
    ShotFamily(
        "oil",
        "oil pump jack",
        ("oil refinery night", "oil barrel"),
        ("petrol", "rafineri", "oil rig"),
    ),
    ShotFamily(
        "farm",
        "farm field aerial",
        ("tractor field", "wheat harvest"),
        ("tarla", "traktor", "ciftlik", "harvest"),
    ),
    ShotFamily(
        "market",
        "street market crowd",
        ("bazaar stalls", "grocery shelves"),
        ("pazar yeri", "carsı", "carsi", "market stall"),
    ),
    ShotFamily(
        "prison",
        "prison corridor",
        ("jail bars close up", "empty cell"),
        ("hapishane", "prison", "parmaklik"),
    ),
    ShotFamily(
        "crown",
        "crown jewels",
        ("royal palace hall", "throne room"),
        ("tac", "kralice", "kral ", "saray", "throne", "queen", "king crown"),
    ),
    ShotFamily(
        "painting",
        "art museum painting",
        ("painter brush canvas", "gallery wall"),
        ("tablo", "muze", "ressam", "painting"),
    ),
    ShotFamily(
        "camera",
        "camera lens close up",
        ("photographer shooting", "film camera vintage"),
        ("kamera", "fotograf makinesi", "lens"),
    ),
    ShotFamily(
        "newspaper",
        "newspaper printing press",
        ("newsroom desk", "press conference microphones"),
        ("gazete", "matbaa", "basin toplantisi", "newsroom"),
    ),
    ShotFamily(
        "guitar",
        "guitar playing hands",
        ("music studio", "piano keys close up"),
        ("gitar", "piyano", "guitar", "piano"),
    ),
    ShotFamily(
        "coffee_shop",
        "cafe interior",
        ("people talking cafe", "laptop cafe table"),
        ("kafe", "cafe"),
    ),
)


_BY_LENGTH: List[tuple] = []
for _fam in FAMILIES:
    for _needle in _fam.needles:
        _BY_LENGTH.append((len(fold(_needle)), _needle, _fam))
_BY_LENGTH.sort(key=lambda row: row[0], reverse=True)


def match_shot(*parts: str) -> Optional[ShotFamily]:
    """Longest concrete noun in the text. Title is a fallback, not a override."""
    blob = fold(" ".join(p for p in parts if p))
    if len(blob) < 3:
        return None
    for _length, needle, fam in _BY_LENGTH:
        if _has_phrase(blob, needle):
            return fam
    return None


def family_of_phrase(phrase: str) -> Optional[ShotFamily]:
    folded = fold(phrase)
    if not folded:
        return None
    for fam in FAMILIES:
        names = [fold(fam.primary), fold(fam.root)] + [fold(v) for v in fam.variants]
        if folded in names:
            return fam
        if fold(fam.root) in folded:
            return fam
    return None


def next_variant(primary: str, index: int) -> Optional[str]:
    """Another camera angle of the same subject. None when the phrase is not locked."""
    fam = family_of_phrase(primary)
    if fam is None:
        return None
    cycle = [fam.primary, *list(fam.variants)]
    alts = [item for item in cycle if fold(item) != fold(primary)]
    if not alts:
        return None
    return alts[abs(int(index)) % len(alts)]


_FILLER_QUERIES = {
    "nature", "cinematic", "cinematic atmosphere", "n/a", "tbd", "none",
}
_GENERIC_FALLBACK_WORDS = {"nature", "sunrise", "landscape", "scenery", "broll", "footage"}


def queries_for_scene(
    narration: str = "",
    scene_description: str = "",
    subject: str = "",
    existing: Optional[Sequence[str]] = None,
    limit: int = 4,
) -> List[str]:
    """Keep queries that name the sentence's subject. Drop nature and atmosphere filler."""
    shot = match_shot(narration, scene_description, subject)
    raw = [str(q).strip() for q in (existing or []) if str(q).strip()]
    if shot is not None:
        kept = [
            q for q in raw
            if query_matches_clip(shot.primary, q) or query_matches_clip(q, shot.primary)
        ]
        merged: List[str] = []
        seen = set()
        for q in list(shot_queries(shot, limit=limit)) + kept:
            key = fold(q)
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(q)
            if len(merged) >= limit:
                break
        return merged
    return [
        q for q in raw
        if fold(q) not in _FILLER_QUERIES
        and not (_GENERIC_FALLBACK_WORDS & set(fold(q).split()))
    ][:limit]


def lock_scene_queries(scene: dict) -> None:
    """Rewrite one generated scene so search queries film the sentence."""
    intent = scene.get("visual_intent") if isinstance(scene.get("visual_intent"), dict) else {}
    existing = scene.get("search_queries") or []
    if isinstance(existing, str):
        existing = [existing]
    queries = queries_for_scene(
        narration=str(scene.get("narration") or ""),
        scene_description=str(scene.get("scene_description") or ""),
        subject=str(intent.get("subject") or ""),
        existing=existing,
    )
    scene["search_queries"] = queries
    shot = match_shot(
        str(scene.get("narration") or ""),
        str(scene.get("scene_description") or ""),
        str(intent.get("subject") or ""),
    )
    if shot is None:
        return
    updated = dict(intent)
    updated["subject"] = shot.primary
    updated["search_queries"] = queries
    updated["visual_priority"] = updated.get("visual_priority") or "subject"
    scene["visual_intent"] = updated


def shot_queries(family: ShotFamily, limit: int = 4) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in (family.primary, *family.variants):
        key = fold(raw)
        if key in seen:
            continue
        seen.add(key)
        out.append(raw)
        if len(out) >= limit:
            break
    return out


# Tokens that appear in almost every stock title. They must not
# count as proof that a skyscraper query matched a beach clip.
WEAK_TOKENS = {
    "light", "dark", "night", "day", "closeup", "close", "detail", "aerial",
    "soft", "natural", "city", "view", "people", "person", "street", "water",
    "sky", "road", "room", "hand", "hands", "background", "video", "clip",
    "footage", "stock", "slow", "motion", "shot", "scene", "beautiful",
    "cinematic", "atmospheric", "wide", "over", "with", "from", "into",
}


def strong_tokens(query: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z]{4,}", fold(query))
    return [t for t in tokens if t not in WEAK_TOKENS]


def query_matches_clip(query: str, clip_text: str) -> bool:
    """True when the clip text actually names the shot, not a weak neighbor word."""
    strong = strong_tokens(query)
    if not strong:
        return True
    blob = fold(clip_text)
    return any(token in blob for token in strong)
