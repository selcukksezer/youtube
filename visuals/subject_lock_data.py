"""Static subject/shot family dictionary tables for concrete shot locking."""
from __future__ import annotations

from dataclasses import dataclass


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
        ("mikroskop", "laboratuvar", "microscope", "bilimsel deney", "laboratuvar deneyi"),
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
        ("car engine close up", "night city driving", "supercar detail", "hypercar track"),
        ("ferrari", "lamborghini", "supercar", "hypercar", "spor araba", "otomobil", "araba", "surus", "kokpit"),
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
        ("runner on road", "barbell close up", "athletic training", "dumbbells workout"),
        ("fitness", "spor salonu", "halter", "kosu", "gym", "antrenman", "kas", "egzersiz", "diyet", "beslenme"),
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
        ("judge gavel", "law books shelf", "scales of justice", "legal document sign"),
        ("mahkeme", "hakim", "courtroom", "gavel", "avukat", "hukuk", "dava", "kanun", "tazminat"),
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
        "ai_tech",
        "artificial intelligence neural network",
        ("computer code developer screen", "future ai digital technology", "software engineer workstation", "digital data cyber interface"),
        ("yapay zeka", "artificial intelligence", "chatgpt", "midjourney", "deepseek", "makine ogrenimi", "sinir agi", "neural network"),
    ),
    ShotFamily(
        "software_coding",
        "software developer coding screen",
        ("programming code monitor", "web design user interface", "developer typing keyboard", "data analysis dashboard"),
        ("yazilim", "kodlama", "programlama", "web sitesi", "website", "yazilimci", "developer", "source code"),
    ),
    ShotFamily(
        "parenting_child",
        "happy family parents and child",
        ("toddler learning playing", "mother baby caring gentle", "kids playground indoor"),
        ("ebeveyn", "ebeveynler", "bebek", "bebekler", "bebegi", "bebeginiz", "cocuk", "cocuklar", "cocugunuz", "anne", "anneler", "baba", "babalar", "aile", "toddler", "parenting"),
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
