/**
 * Proje bazli MV cesitliligi.
 *
 * Ayni sarki icinde klipler TEK filmin ardışık saniyeleridir (dunya / kostum /
 * karakter kilitli). Farkli projelerde binlerce kullanici ayni tilki + sari
 * sahne + "Pixar" kalibina dusmesin diye art dialect, dunya, siluet, palet,
 * kamera ve jest havuzlari proje id'sinden deterministik secilir.
 */

import { parseSongSettings } from "@/lib/song-settings";

export type VarietyItem = { id: string; prompt: string };

export type SongVarietyPack = {
  seed: number;
  packId: string;
  artDialect: VarietyItem;
  world: VarietyItem;
  silhouette: VarietyItem;
  speciesHint: VarietyItem;
  palette: VarietyItem;
  lighting: VarietyItem;
  outfit: VarietyItem;
  materialLanguage: string;
  weather: string;
  exteriorWorld: string;
  coldOpen: string;
  handoff: string;
  moodFamily: "bright" | "tender" | "adventure" | "cozy";
  shotStylePhrase: string;
  characterRenderStyle: string;
  turnaroundIdentityLine: string;
  styleLabel: string;
};

export type ClipVarietyAccent = {
  camera: string;
  lightingAccent: string;
  choreo: string;
  choreoTr: string;
  emotion: string;
  voiceTone: string;
  beatVerb: (second: number) => string;
};

type SeedSource = {
  id: string;
  createdAt?: Date | string | null;
  songSettings?: string | null;
  emotionCurve?: string | null;
};

const ART_DIALECTS: VarietyItem[] = [
  {
    id: "gloss-cgi",
    prompt:
      "Theatrical glossy 3D CGI family animation, physically based materials, wet living eyes, soft global illumination, feature-film subsurface scattering — NOT live-action, NOT 2D. Distinct from generic toy-commercial smoothness: rich bounce color, cinematic shallow DOF, groomed fur strands.",
  },
  {
    id: "felt-plush",
    prompt:
      "Handmade felt-and-plush 3D CGI: visible needle-felt fiber, stitched seams, wool-pile fur, button-like but living eyes, soft fabric weight. Still full 3D animation (not stop-motion plates), cozy craft-film look, tactile close-ups.",
  },
  {
    id: "clay-cgi",
    prompt:
      "Claymation-look 3D CGI: soft thumbprint material, rounded clay volumes, slightly matte plasticine sheen, gentle squash. Animated in 3D with cinematic lighting — not real stop-motion flicker, not live-action.",
  },
  {
    id: "wood-toy",
    prompt:
      "Painted wooden-toy-world 3D CGI: visible wood grain under enamel paint in the sets, rounded peg joints, smooth carved curves, lacquer sheen. Warm workshop lighting, storybook toy theater; characters are smooth rounded organic forms (never block-carved, never boxy), fully animated 3D.",
  },
  {
    id: "candy-glass",
    prompt:
      "Candy-glass storybook 3D CGI: translucent sugar surfaces, rounded confection architecture, glossy icing highlights, gummy translucency, sprinkles as set dressing. Feature lighting, never food-horror, never live-action.",
  },
  {
    id: "knit-yarn",
    prompt:
      "Knit-and-yarn 3D CGI: visible knitted stitches, pom-pom texture, embroidered patches, yarn-hair strands, soft wool bounce. Cozy craft animation, physically based fabric, cinematic GI.",
  },
  {
    id: "paper-diorama",
    prompt:
      "Paper-craft diorama 3D CGI: folded cardstock planes and layered paper trees in the BACKGROUNDS, soft paper-fiber close-ups, gentle theater-box lighting. Characters are smooth rounded 3D mascots with subtle paper texture (never folded, faceted or angular bodies), fully animated.",
  },
  {
    id: "ceramic",
    prompt:
      "Glazed ceramic-figurine 3D CGI: porcelain skin with tiny craquelure, painted-on blush, glossy glaze catches, ceramic weight in footsteps. Friendly figurine mascots, feature-film lighting, not brittle horror.",
  },
  {
    id: "balloon",
    prompt:
      "Balloon-sculpture 3D CGI: inflated vinyl-sheen volumes, twisted balloon joints, bright latex highlights, floaty squash-and-stretch. Playful parade-float mascots, cinematic GI, never scary deflation.",
  },
  {
    id: "enamel-tin",
    prompt:
      "Enamel tin-toy 3D CGI: baked enamel colors, tiny rivets, lithograph print texture (unreadable patterns only), wind-up toy charm, metal glints. Fully animated 3D, warm practical lighting.",
  },
  {
    id: "velvet-puppet",
    prompt:
      "Velvet-puppet 3D CGI: crushed-velvet pile catching light, felt mouths, embroidered brows, theater-spot key light with dusty god-rays. Premium puppet-film CGI, not live-action, not 2D.",
  },
  {
    id: "mosaic",
    prompt:
      "Mosaic-tile world 3D CGI: tiny glazed tesserae on architecture, grout lines, ceramic sparkle, characters as smooth stylized 3D mascots against mosaic sets. Bright Mediterranean bounce light.",
  },
  {
    id: "origami",
    prompt:
      "Origami-inspired 3D CGI: washi paper fiber, ink-wash sky (no readable glyphs), gentle folded accents on CLOTHES and set dressing only. Characters stay cute smooth rounded mascots (never faceted low-poly or angular folded bodies), fully animated, cinematic light.",
  },
  {
    id: "soap-iris",
    prompt:
      "Iridescent soap-bubble 3D CGI: thin-film rainbow sheen on props and dew, pearly highlights, soft pastel volumes, airy bounce. Gentle dreamy family CGI, never psychedelic clutter.",
  },
  {
    id: "embroidery",
    prompt:
      "Embroidered-tapestry 3D CGI: satin-stitch clothes, french-knot flowers in sets, visible thread thickness, hoop-frame architecture. Characters are plush-stitched mascots, cinematic lighting.",
  },
  {
    id: "brick-toy",
    prompt:
      "Glossy toy-playroom 3D CGI: rounded toy-block architecture in the SETS only (soft edges, no studs on characters), characters are smooth rounded organic plush-vinyl mascots — never brick-built, never cube-shaped, never minifigure-like, never voxel — soft vinyl sheen, playful primary colors, cinematic GI.",
  },
  {
    id: "sandcastle",
    prompt:
      "Sunbaked sand-castle 3D CGI: packed sand grain, drip-castle towers, shell mosaics, warm beach bounce, wet-sand darker zones. Stylized 3D mascots with sandy paw pads, never grit-horror.",
  },
  {
    id: "frost-sugar",
    prompt:
      "Frost-sugar cookie 3D CGI: royal-icing outlines, sugar-crystal sparkle, baked golden edges, candy-button details. Winter-bakery warmth, feature lighting, never food-gross.",
  },
  {
    id: "clockwork",
    prompt:
      "Brass-clockwork toy 3D CGI: visible friendly gears (no sharp danger), warm brass and copper, enamel numerals unreadable, ticking-set motion. Soft steampunk-toy charm, kids-safe, cinematic GI.",
  },
  {
    id: "watercolor-vol",
    prompt:
      "Watercolor-volume 3D CGI: 3D forms with painted pigment edges, paper-grain in backgrounds, bleeding color washes, kept fully 3D (not 2D anime). Storybook illustration shaders, gentle cinematic light.",
  },
  {
    id: "garden-gnome",
    prompt:
      "Garden-porcelain gnome-cottage 3D CGI: rosy ceramic cheeks, mossy stone cottages, flower-hat costumes, enamel highlights. Friendly mascot figurines, golden garden light, never uncanny.",
  },
  {
    id: "stained-light",
    prompt:
      "Stained-glass light 3D CGI: colored light pools on the floor, jewel-tone windows with UNREADABLE patterns, characters as smooth stylized 3D mascots bathed in colored bounce. Cathedral-playful, not religious sermon.",
  },
  {
    id: "foam-park",
    prompt:
      "Soft-play foam-park 3D CGI: matte foam blocks, rounded safety corners, primary vinyl mats, chunky mascot bodies. Play-center energy, cinematic lighting, tactile foam dents on contact.",
  },
  {
    id: "marzipan",
    prompt:
      "Marzipan-sculpt 3D CGI: almond-paste matte skin, painted food-color cheeks, sugar-dusted sets, bakery-window warmth. Cute confection mascots, feature GI, never creepy food-people.",
  },
];

const WORLDS: VarietyItem[] = [
  { id: "lantern-harbor", prompt: "floating lantern harbor at warm dusk: wooden piers, unreadable bunting, bobbing lamps, wet planks, distant tiny bouncing extras on boats" },
  { id: "candy-courtyard", prompt: "candy-tile courtyard with a working fountain, sugar-mosaic floor, icing-trim balconies, steam from cocoa carts (no readable signs)" },
  { id: "mushroom-amp", prompt: "mushroom amphitheater in a moss forest: cap-roofs, spore-sparkle in god-rays, log benches, fern foreground" },
  { id: "oasis-plaza", prompt: "desert oasis music plaza: palm shade, turquoise pool, terracotta tiles, brass lanterns, sand grain underfoot" },
  { id: "snowglobe", prompt: "snow-globe village square: packed snow paths, warm window glow (unreadable), pine boughs, falling flakes on the beat" },
  { id: "kelp-hall", prompt: "sunlit kelp concert hall (air-filled, not drowning): cathedral kelp, caustic light on sandy floor, bubble motes, coral balconies" },
  { id: "rooftop-garden", prompt: "rooftop garden festival: planters, string lights, city-toy skyline far away, laundry flags (unreadable), brick underfoot" },
  { id: "kite-meadow", prompt: "paper-kite meadow: tall grass, wildflowers, kites on the wind, dirt path, distant hill windmill" },
  { id: "tram-plaza", prompt: "tram-stop plaza with bunting: cobbles, flower boxes, a colorful tram (no readable destination), cafe awnings without letters" },
  { id: "greenhouse", prompt: "greenhouse disco-garden: glass panes, condensation, tropical leaves, hanging planters, colored gel sunlight" },
  { id: "boardwalk", prompt: "riverside wooden boardwalk: peeling paint rails, paddleboats, willow trees, bouncing reflections" },
  { id: "windmill-picnic", prompt: "hilltop windmill picnic: checkered cloth, spinning sails, wildflower slope, kite-dots in sky" },
  { id: "skyport", prompt: "balloon-dock skyport: tied giant friendly balloons, rope nets, cloud floor gaps, brass cleats" },
  { id: "tile-court", prompt: "colorful tiled courtyard with a shallow reflecting pool, mosaic walls, citrus trees in pots, hanging rugs (unreadable patterns)" },
  { id: "orchard-stage", prompt: "orchard harvest stage: apple crates, ladder, blossom or fruit (season-locked), grass, wooden platform" },
  { id: "seaside-carousel", prompt: "seaside boardwalk near a gentle carousel (no logos): salt air haze, painted horses, popcorn-cart steam, wet sand edge" },
  { id: "cable-station", prompt: "mountain cable-car station: timber, snow caps, colorful gondolas, prayer-flag-like cloth strips without text" },
  { id: "pastel-moon", prompt: "soft pastel lunar playground: gentle craters as sandpits, candy-colored craters, Earth-marble in sky, bouncy low-gravity feel but planted feet" },
  { id: "bakery-street", prompt: "bakery-street at golden hour: unreadable shopfronts, bread-basket props, flour dust motes, warm brick" },
  { id: "library-garden", prompt: "library-garden with reading nooks: hedges, stone paths, closed books with UNREADABLE spines, lanterns" },
  { id: "ice-plaza", prompt: "ice-cream parlor plaza: pastel umbrellas, swirl-sculpture fountain, tiled floor, dripping-safe cute scoops as set dressing" },
  { id: "leaf-bandstand", prompt: "autumn leaf park bandstand: orange canopy, brass gazebo, leaf-fall on the beat, acorn piles" },
  { id: "blossom-tunnel", prompt: "spring blossom tunnel: pink petals, stone path, paper lanterns, petal-rain on chorus" },
  { id: "puddle-street", prompt: "rain-puddle street with bright umbrellas: wet cobbles, neon-free colorful bounce, splash rings, cozy windows" },
  { id: "campsite", prompt: "gentle starlit campsite: warm tent glow, safe campfire sparkles, log seats, firefly motes — cozy not scary" },
  { id: "toy-station", prompt: "toy-train station plaza: chunky tracks, numbered wagons as lyric props when needed, clock without readable time, flower beds" },
  { id: "watercolor-harbor", prompt: "watercolor harbor: painted-sail boats, pigment-bleed sky, wooden docks, gull silhouettes bouncing tiny" },
  { id: "cactus-shelf", prompt: "cactus canyon music shelf: striped rock, bloom tips, shade pockets, tambourine-echo space, sandy floor" },
  { id: "cloud-bridge", prompt: "cloud-bridge between floating islands: cotton-cloud rails, pastel cliffs, hanging gardens, wind socks (unreadable)" },
  { id: "firefly-meadow", prompt: "warm firefly meadow at blue hour: safe golden dots, wooden stage, tall grass, distant cottage glow" },
  { id: "market-canopy", prompt: "spice-color market canopies: stacked fruit (countable if lyrics need), hanging pots, patterned cloth without letters, stone aisle" },
  { id: "lighthouse-cove", prompt: "lighthouse cove: candy-stripe tower (no text), tide pools, pebbles, gull extras, rotating warm beam" },
];

const SILHOUETTES: VarietyItem[] = [
  { id: "round-cub", prompt: "extra-round squash-and-stretch cub body, short limbs, huge head, bean-feet" },
  { id: "lanky-felt", prompt: "lanky-limbed felt performer, long legs, small torso, oversized boots" },
  { id: "dumpling", prompt: "compact dumpling body, tiny wings or ears, heavy cute center of gravity" },
  { id: "beanpole", prompt: "tall beanpole mascot, huge boots, skinny arms, bobble head" },
  { id: "pear", prompt: "pear-shaped mascot, wide hips, tiny feet, proud chest" },
  { id: "plush-hands", prompt: "tiny head, enormous friendly hands, plush-chunk proportions" },
  { id: "porcelain-eleg", prompt: "elegant porcelain proportions, longer neck, dainty paws, still cute not adult-human" },
  { id: "stocky-toy", prompt: "stocky toy-soldier compact build, square shoulders, short stride" },
  { id: "teardrop", prompt: "teardrop body, no visible neck, flipper-like arms, bounce-first locomotion" },
  { id: "gourd", prompt: "gourd-shaped torso, spiral tail, sprout-hair tuft" },
  { id: "loaf", prompt: "loaf-cat compact rectangle body, stubby legs, wide face" },
  { id: "kite-frame", prompt: "diamond-kite torso, ribbon limbs, light wind-reactive silhouette" },
  { id: "acorn", prompt: "acorn-cap head, round nut body, twig limbs" },
  { id: "bell", prompt: "bell-shaped skirted body (costume, not human), tiny legs peeking, swing-walk" },
  { id: "cloud-puff", prompt: "cloud-puff spherical body, stubby paws, vapor-soft edges that stay on-model" },
  { id: "barrel", prompt: "friendly barrel chest, short legs, heroic chin (animal, not human child)" },
];

const SPECIES: VarietyItem[] = [
  { id: "fennec-star", prompt: "fennec-fox mascot with star-tufted ear tips" },
  { id: "owl-conductor", prompt: "round owl mascot in a tiny conductor vibe (species only — outfit from wardrobe bank)" },
  { id: "raccoon-scarf", prompt: "raccoon mascot with a bold mask marking" },
  { id: "penguin-beanie", prompt: "penguin mascot with a round tummy and flipper-hands" },
  { id: "otter-pebble", prompt: "river otter mascot, whiskered, pebble-smart paws" },
  { id: "raincoat-fox", prompt: "red-fox mascot with a sharp muzzle and fluffy tail" },
  { id: "panda-baker", prompt: "panda mascot, piebald patches, round ears" },
  { id: "chameleon", prompt: "chameleon mascot with gentle swivel eyes (color-play, not scary)" },
  { id: "squirrel-aviator", prompt: "squirrel mascot with a bottlebrush tail" },
  { id: "hedgehog-garden", prompt: "hedgehog mascot with soft rounded quills" },
  { id: "frog-boots", prompt: "frog mascot with a wide smile and spring legs" },
  { id: "koala-overall", prompt: "koala mascot with fluffy ears and a button nose" },
  { id: "llama-tassel", prompt: "llama mascot with banana-ears and a banana-smile" },
  { id: "redpanda", prompt: "red-panda mascot, rust fur, ringed tail" },
  { id: "axolotl-sailor", prompt: "axolotl mascot with frilly gills, peach-pink, always smiling" },
  { id: "bee-goggles", prompt: "round bee mascot, striped, tiny wings, friendly not stinging" },
  { id: "turtle-drum", prompt: "turtle mascot with a patterned shell (unreadable)" },
  { id: "wolf-denim", prompt: "friendly wolf-cub mascot, soft not fanged-horror" },
  { id: "mouse-tailor", prompt: "mouse mascot with round ears and a long balancing tail" },
  { id: "duck-slicker", prompt: "duck mascot with orange feet and a cheerful bill" },
  { id: "capybara-crown", prompt: "capybara mascot, calm square snout, chill posture" },
  { id: "kiwi-explore", prompt: "kiwi-bird mascot, long gentle bill, hair-like feathers" },
  { id: "narwhal-balloon", prompt: "sky-narwhal mascot (cute floating, tiny fins, spiral horn as a candy cane shape)" },
  { id: "moth-librarian", prompt: "moth mascot with powdery wings and feathery antennae" },
  { id: "crab-perc", prompt: "hermit-crab mascot in a painted shell house, tiny marching legs" },
  { id: "cactus-cat", prompt: "cactus-cat hybrid mascot: cat face, soft cactus-ear pads, bloom on head — not spiky-pain" },
  { id: "cloud-sheep", prompt: "cloud-sheep mascot, puff-wool, sky-blue nose" },
  { id: "star-beetle", prompt: "star-beetle mascot, round shell with star spots, tiny friendly horns" },
  { id: "lantern-fish", prompt: "cute lantern-fish mascot, warm lamp-lure, big kind eyes, never deep-sea horror" },
  { id: "moss-bear", prompt: "moss-bear cub mascot, lichen patches, forest-green fur tips" },
  { id: "puffin", prompt: "puffin mascot with a colorful bill and orange feet" },
  { id: "alpaca", prompt: "alpaca mascot with square-cut bangs-fur and a long neck" },
];

const PALETTES: VarietyItem[] = [
  { id: "apricot-teal", prompt: "apricot, teal, and cream — warm fruit with cool water bounce" },
  { id: "coral-seafoam", prompt: "coral, seafoam, and butter yellow" },
  { id: "lavender-peach", prompt: "lavender, peach, and mint" },
  { id: "sunflower-sky", prompt: "sunflower gold, sky blue, and tomato red accents" },
  { id: "blueberry-lemon", prompt: "blueberry, lemon, and whipped-cream white" },
  { id: "terra-sage", prompt: "terracotta, sage, and antique gold" },
  { id: "candy-lime", prompt: "candy pink, lime, and paper white" },
  { id: "cobalt-mango", prompt: "cobalt, mango, and blush" },
  { id: "forest-butter", prompt: "forest green, buttercup, and rust" },
  { id: "ice-rose", prompt: "ice blue, rose, and silver-white" },
  { id: "honey-plum", prompt: "honey amber, plum, and cream" },
  { id: "olive-coral", prompt: "olive, coral, and sand" },
  { id: "navy-sherbet", prompt: "soft navy, sherbet orange, and vanilla (navy as night-sky, not military)" },
  { id: "lilac-chartreuse", prompt: "lilac, chartreuse, and warm gray" },
  { id: "cocoa-mint", prompt: "cocoa brown, mint, and caramel" },
  { id: "fuchsia-aqua", prompt: "fuchsia, aqua, and lemon zest" },
  { id: "marigold-slate", prompt: "marigold, slate blue, and ivory" },
  { id: "watermelon", prompt: "watermelon pink, rind green, and seed-black tiny accents" },
  { id: "saffron-indigo", prompt: "saffron, indigo, and buttermilk" },
  { id: "pistachio-rose", prompt: "pistachio, dusty rose, and gold thread" },
];

const LIGHTING: VarietyItem[] = [
  { id: "golden-rim", prompt: "golden-hour warm key, peach rim, soft fill, long friendly shadows" },
  { id: "greenhouse-soft", prompt: "overcast-soft greenhouse light, cool fill, leafy caustics" },
  { id: "lantern-magic", prompt: "magic-hour cobalt sky plus warm lantern practicals" },
  { id: "noon-bounce", prompt: "high-noon hard sun softened by colorful bounce from nearby walls" },
  { id: "dusk-tungsten", prompt: "dusk cobalt ambient with tungsten practicals and gentle string lights" },
  { id: "morning-shafts", prompt: "morning window shafts, dust motes, cool shadows, warm interior bounce" },
  { id: "pastel-cloudy", prompt: "cloudy pastel bounce, low contrast, candy-wrapper sky" },
  { id: "sunset-candy", prompt: "sunset candy rim (magenta-orange) with teal fill" },
  { id: "beach-glare", prompt: "noon beach glare with strong fill so faces stay readable, sparkle on water" },
  { id: "festival-night", prompt: "gentle night-festival string lights, never scary dark, faces always keyed" },
  { id: "snow-bounce", prompt: "snow bounce fill, cool skylight, warm window practicals" },
  { id: "undersea-caustic", prompt: "undersea caustic gobos (air set or water set), cyan bounce, gold practicals" },
  { id: "bakery-warm", prompt: "bakery-window warm wrap, butter highlights, chocolate-shadows" },
  { id: "stain-pools", prompt: "stained-glass colored light pools on the floor, white fill on the face" },
  { id: "fog-godray", prompt: "light volumetric fog, god-rays, sparkling particles on the beat" },
  { id: "neon-soft", prompt: "soft neon-gel bounce (pink/cyan) kept pastel and kids-safe, no club darkness" },
];

const OUTFITS: VarietyItem[] = [
  { id: "raincoat", prompt: "shiny raincoat, matching boots, hood down, no logos" },
  { id: "festival-vest", prompt: "festival vest with a sash and tiny bells, no text" },
  { id: "knit-cardigan", prompt: "chunky knit cardigan and a striped scarf" },
  { id: "overalls-star", prompt: "dungarees with a star patch (shape only, no letters)" },
  { id: "conductor", prompt: "tiny conductor coat and a soft cap, playful not military" },
  { id: "baker", prompt: "baker apron (BLANK, no writing) and flour-dusted sleeves" },
  { id: "aviator", prompt: "aviator scarf and round goggles on the forehead" },
  { id: "gardener", prompt: "gardener dungarees, one glove tucked, seed-pouch" },
  { id: "sailor-stripe", prompt: "sailor stripe shirt and a floppy ribbon bow, civilian cute" },
  { id: "dancer-sash", prompt: "dancer sash, wrist bells, soft jazz shoes" },
  { id: "pom-hat", prompt: "winter pom-hat, mittens on a string, wool coat" },
  { id: "sunhat", prompt: "wide sunhat, linen shirt, rolled cuffs" },
  { id: "capelet", prompt: "short capelet and buttoned tunic" },
  { id: "hoodie-shape", prompt: "color-blocked hoodie (no print, no letters) and joggers" },
  { id: "poncho", prompt: "woven poncho with geometric unreadable pattern and boots" },
  { id: "kimono-play", prompt: "playful short happi-like jacket (no crests, no text) and loose pants" },
  { id: "space-knit", prompt: "knit 'space' cardigan with planet-shapes (not NASA logos) and moon boots" },
  { id: "chef-hat", prompt: "puffy chef hat (blank) and checkered pants" },
  { id: "band-tee-blank", prompt: "blank colorful tee, star buttons, rolled shorts" },
  { id: "quilt-coat", prompt: "patchwork quilt coat, each patch a solid color" },
];

const MATERIALS = [
  "close-up readable fiber, stitch, glaze or grain matching THIS art dialect — never generic plastic blobs",
  "every prop has thickness, contact shadow, and a material story (wear, gloss, or pile) locked for the whole song",
  "background architecture uses the same material family as the singer's world — no random styrofoam void",
];

const WEATHERS = [
  "golden hour, clear sky, warm breeze",
  "late afternoon, high thin clouds, candy-colored light",
  "magic hour, cobalt zenith, lantern weather",
  "bright noon, hard sun, colorful bounce, dry air",
  "soft overcast, even light, gentle breeze",
  "after-rain sparkle, puddles, washed air, bright clouds",
  "light snowfall, cozy, faces always lit",
  "blossom-petal drift, spring, mild sun",
  "autumn leaf-fall, amber light, clear",
  "gentle night festival, string-light weather, never pitch-black",
  "sea-mist morning, soft sun disks",
  "desert clear, sharp shadows, oasis cool pockets",
];

const COLD_OPENS = [
  "whip-pan onto planted feet as set lanterns ignite on the downbeat",
  "crane down from kite-filled sky onto the singer already mid-groove",
  "slider past foreground props revealing the singer mid-clap",
  "match-cut from a spinning prop that becomes the singer's first viseme",
  "low hero rise as the world lights layer by layer behind them",
  "orbit 20 degrees onto a planted pose, background extras already bouncing tiny",
  "push through hanging fabric/leaves onto the singer's first syllable",
  "top-shot drop to eye-level as the groove starts, feet already planted",
  "rack from a lyric-prop in extreme close-up to a medium of the singer",
  "sideways dolly along a boardwalk/rail that lands on the singer",
];

const HANDOFFS = [
  "soft settle then continue the bounce into the next bar — same planted feet",
  "hold the lyric-prop toward camera then lower it into the next phrase",
  "glance along the path the next clip will travel, body still grooving",
  "freeze-feel 4 frames of the last viseme then breathe into the next clip",
  "spin a half-turn that completes in the following clip (match-on-action)",
  "step onto the same floor mark, hand still on the named prop",
];

const CAMERAS = [
  "24mm wide stage, slight low, gentle beat-bob",
  "28mm walk-and-talk tracking, planted feet, parallax foreground",
  "35mm medium, eye-level, slow push-in on the hook word",
  "40mm, three-quarter, slider-left 20cm",
  "50mm portrait-on-hook, shallow DOF, background still readable",
  "18mm low hero, sky/architecture tall, no distortion-ugly faces",
  "high 3/4 bird 35mm, then settle to eye-level by last second",
  "gentle orbit 12 degrees, 35mm, keep singer centered",
  "crane-up 40cm over 8s, 32mm",
  "handheld-feel CG sway 2cm, 40mm, never nauseous",
  "slider-right parallax past a lyric-prop, 28mm",
  "push-in 15% on the last syllable, 50mm",
  "over-shoulder 35mm of the prop then whip to singer face (same take feel)",
  "profile 50mm walking-groove, then face camera on the rhyme",
  "top-down 24mm dance-map then drop to medium",
  "two-shot wide 24mm if support cast exists, else wide empty-safe with extras tiny",
  "macro insert 1s on prop material then snap-back to 35mm medium (continuous take)",
  "dutch 3 degrees max, 35mm, playful not horror",
  "rear 3/4 40mm of costume then orbit to front",
  "low 21mm along the ground, then rise to chest height",
];

const LIGHT_ACCENTS = [
  "chorus lift: 10% key bump + sparkle motes",
  "practical lanterns pulse 5% on the downbeat",
  "rim color shifts half-stop toward the palette accent",
  "fill warms for the smile, cools for the count",
  "god-ray density increases on the hook word",
  "string-lights twinkle in tempo, faces stay steady",
  "caustics crawl slower, bounce stays locked",
  "window shaft dust motes hit on snare-like beats",
];

const CHOREO: Array<{ en: string; tr: string }> = [
  { en: "stamp-plant on the downbeat, then present the named prop", tr: "vuruşta yere basar, adlı prop'u gösterir" },
  { en: "shoulder-roll + clap-high, then tap the lyric object", tr: "omuz yuvarlar, yukarı alkışlar, prop'a dokunur" },
  { en: "hop-land with bent knees, prop stays in frame", tr: "diz bükülü zıplar-iner, prop karede kalır" },
  { en: "spin-once (slow, planted), then point-count", tr: "yavaş bir tur döner, sonra sayarak işaret eder" },
  { en: "lean-into-cam 10cm, viseme big, then bounce back", tr: "kameraya hafif yaslanır, heceyi büyütür" },
  { en: "kick-ball-change, then scoop-lift the prop", tr: "adım-topuk değişir, prop'u yukarı kaşıklar" },
  { en: "twirl a scarf/sash, then plant and sing", tr: "kuşağı çevirir, basar ve söyler" },
  { en: "side-step groove, ears/tail on the offbeat", tr: "yan adım groove, kulak/kuyruk vuruş dışında" },
  { en: "crouch-bounce, then pop up on the rhyme", tr: "çömelip zıplar, kafiyede ayağa fırlar" },
  { en: "arm-wave figure-eight, then both paws on the prop", tr: "sekiz çizer, iki pati prop'ta" },
  { en: "heel-toe walk in place, then freeze-pose smile", tr: "yerinde topuk-uç yürür, gülümser" },
  { en: "jump-tuck tiny, land sticky, present prop", tr: "minik zıplama, yapışık iniş, prop sunumu" },
  { en: "slide-step (feet still planting, no ice-skate)", tr: "adım kaydırır ama ayak basar, buz pateni yok" },
  { en: "call-and-response clap with distant extras", tr: "uzaktaki ekstralarla alkış çağrı-yanıt" },
  { en: "prop-orbit around the body, then hug it to chest", tr: "prop'u etrafında gezdirir, göğse çeker" },
  { en: "march-in-place, then big viseme on the last word", tr: "yerinde yürür, son kelimede büyük ağız" },
];

const BEAT_VERBS = [
  "syllable viseme + knee bounce",
  "tap the named prop on the lyric hit",
  "ear-flick on the beat",
  "tail-swish counter to the groove",
  "fabric follow-through after a clap",
  "camera micro-push 2%",
  "background extra hop (tiny, far)",
  "sparkle/particle pulse",
  "foot-plant dust puff",
  "blink-smile",
  "brow lift on the question-word",
  "shoulder shimmy 2 beats",
  "weight shift left-right",
  "prop glint timed to the vowel",
  "head nod on the snare-feel",
  "paw-point along lyric order",
  "cheek puff then release",
  "hat/scarf bounce",
  "secondary ear overlap",
  "background flag/leaf twitch",
  "rim-light flicker 5%",
  "spin a wrist once",
  "crouch 4cm then rise",
  "look at prop then to camera",
];

const EMOTIONS: Record<SongVarietyPack["moodFamily"], string[]> = {
  bright: ["neşeli", "coşkulu", "oyuncu", "gururlu", "şaşkın-mutlu"],
  tender: ["yumuşak", "şefkatli", "hayran", "meraklı", "neşeli"],
  adventure: ["kararlı", "meraklı", "coşkulu", "şaşkın-mutlu", "gururlu"],
  cozy: ["yumuşak", "oyuncu", "şefkatli", "neşeli", "hayran"],
};

const VOICE_TONES: Record<SongVarietyPack["moodFamily"], string[]> = {
  bright: [
    "bright and bouncy, smiling singing face",
    "sparkly high energy, wide visemes",
    "proud belt with a grin",
    "giggly bounce then clear diction",
  ],
  tender: [
    "warm hush-then-lift, soft eyes",
    "honeyed midrange, gentle bounce",
    "storyteller sway, kind brows",
    "lullaby-adjacent but still on-groove",
  ],
  adventure: [
    "clear counting cadence, brave posture",
    "forward-lean explorer energy",
    "proud belt, wind in fabric",
    "curious darting glances then plant",
  ],
  cozy: [
    "warm kitchen-light smile",
    "soft bounce, cozy shoulders",
    "hug-the-prop affection",
    "sleepy-sparkle eyes, still on beat",
  ],
};

const MOOD_FAMILIES: SongVarietyPack["moodFamily"][] = ["bright", "tender", "adventure", "cozy"];

/**
 * KARE KARE YASAGI — karakter govdesi hicbir lehcede kup/voksel/tugla olamaz.
 * Malzeme lehcesi setlere doku verir; karakter her zaman yumusak ve yuvarlaktir.
 */
export const SMOOTH_CHARACTER_LOCK =
  "Character bodies stay smooth, rounded and organic — never voxel, cube-built, brick-built, faceted low-poly, pixelated or Minecraft/Lego-like; the material dialect textures the SETS, never the body shape.";

export function hash32(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function pick<T>(items: readonly T[], seed: number, lane: number): T {
  const mixed = Math.imul(seed ^ Math.imul(lane + 1, 2654435761), 1597334677) >>> 0;
  return items[mixed % items.length]!;
}

function parseVarietySeedFromCurve(raw?: string | null): number | null {
  if (!raw?.trim()) return null;
  try {
    const parsed = JSON.parse(raw) as { varietySeed?: unknown };
    return typeof parsed.varietySeed === "number" && Number.isFinite(parsed.varietySeed)
      ? parsed.varietySeed >>> 0
      : null;
  } catch {
    return null;
  }
}

export function seedFromProject(project: SeedSource): number {
  const fromCurve = parseVarietySeedFromCurve(project.emotionCurve);
  if (fromCurve != null) return fromCurve;
  const settings = parseSongSettings(project.songSettings);
  if (typeof settings.varietySeed === "number" && Number.isFinite(settings.varietySeed)) {
    return settings.varietySeed >>> 0;
  }
  const created =
    project.createdAt instanceof Date ? project.createdAt.toISOString() : String(project.createdAt ?? "");
  return hash32(`${project.id}|${created}`);
}

export function buildSongVarietyPackFromSeed(seed: number): SongVarietyPack {
  const artDialect = pick(ART_DIALECTS, seed, 1);
  const world = pick(WORLDS, seed, 2);
  const silhouette = pick(SILHOUETTES, seed, 3);
  const speciesHint = pick(SPECIES, seed, 4);
  const palette = pick(PALETTES, seed, 5);
  const lighting = pick(LIGHTING, seed, 6);
  const outfit = pick(OUTFITS, seed, 7);
  const materialLanguage = pick(MATERIALS, seed, 8);
  const weather = pick(WEATHERS, seed, 9);
  const coldOpen = pick(COLD_OPENS, seed, 10);
  const handoff = pick(HANDOFFS, seed, 11);
  const moodFamily = pick(MOOD_FAMILIES, seed, 12);
  const packId = `${artDialect.id}-${world.id}-${silhouette.id}-${palette.id}`;

  const shotStylePhrase = `${artDialect.id.replace(/-/g, " ")} 3D animated music-video shot`;
  const characterRenderStyle = [
    artDialect.prompt,
    `Silhouette dialect: ${silhouette.prompt}.`,
    `Material language: ${materialLanguage}.`,
    "Feature-film render quality, physically based materials, every fiber/fabric/glaze faithful to THIS dialect.",
    "Stylized 3D cartoon mascot / fantasy performer — never a human child or minor.",
    "Maximum toddler-appeal cuteness: huge sparkling eyes with layered catchlights, plump round cheeks with soft blush, tiny button nose, rounded huggable edges — irresistibly adorable, richly detailed, never creepy, never generic.",
    SMOOTH_CHARACTER_LOCK,
  ].join(" ");

  return {
    seed,
    packId,
    artDialect,
    world,
    silhouette,
    speciesHint,
    palette,
    lighting,
    outfit,
    materialLanguage,
    weather,
    exteriorWorld: `${world.prompt}. Ground + sky/weather ceiling + horizon + distant living extras. Time/weather: ${weather}.`,
    coldOpen,
    handoff,
    moodFamily,
    shotStylePhrase,
    characterRenderStyle,
    turnaroundIdentityLine: `Same single stylized 3D character in BOTH panels — identical face, species, colors, costume and proportions — rendered in this project's ${artDialect.id} dialect (not a generic studio mascot).`,
    styleLabel: artDialect.id,
  };
}

export function resolveSongVarietyPack(project: SeedSource): SongVarietyPack {
  return buildSongVarietyPackFromSeed(seedFromProject(project));
}

export function clipVarietyAccent(pack: SongVarietyPack, clipIndex: number): ClipVarietyAccent {
  const idx = Math.max(1, Math.round(clipIndex) || 1);
  const camera = pick(CAMERAS, pack.seed, 100 + idx);
  const lightingAccent = pick(LIGHT_ACCENTS, pack.seed, 200 + idx);
  const choreo = pick(CHOREO, pack.seed, 300 + idx);
  const emotions = EMOTIONS[pack.moodFamily];
  const tones = VOICE_TONES[pack.moodFamily];
  return {
    camera,
    lightingAccent,
    choreo: choreo.en,
    choreoTr: choreo.tr,
    emotion: pick(emotions, pack.seed, 400 + idx),
    voiceTone: pick(tones, pack.seed, 500 + idx),
    beatVerb: (second: number) => pick(BEAT_VERBS, pack.seed, 8000 + idx * 17 + Math.max(0, second)),
  };
}

export function formatCastVarietyLock(pack: SongVarietyPack): string {
  return `THIS PROJECT'S UNIQUE CAST LOOK (locked for the whole song — do NOT default to a generic orange fox in a red hoodie on a yellow void):
- Art dialect: ${pack.artDialect.prompt}
- Silhouette: ${pack.silhouette.prompt}
- Species FAMILY flavor for this song (a direction, NOT one shared species): ${pack.speciesHint.prompt}
  Every cast member must still be a DIFFERENT creature with a different body shape, height band and main color.
- Outfit dialect: ${pack.outfit.prompt} (BLANK garments — no letters, logos, or readable prints)
- Palette: ${pack.palette.prompt}
- imagePrompt: English, full body, broadcast-safe stylized 3D mascot, written IN this art dialect (do not write "Pixar-style" or copy a famous studio).
- Each member must be visually distinct within the SAME dialect and world, not clone-recolors.
- Never output two members that could share one character sheet — different species, silhouette, height and main color, every time.`;
}

export function formatVisualsVarietyLock(pack: SongVarietyPack): string {
  return `THIS PROJECT'S UNIQUE MV LOOK (locked for ALL clips of this song — consecutive seconds of ONE film):
- Art dialect (use this instead of a generic Pixar/yellow-stage default): ${pack.artDialect.prompt}
- World geography for the WHOLE song: ${pack.world.prompt}
- Weather / time of day LOCK: ${pack.weather}
- Exterior depth: ${pack.exteriorWorld}
- Lighting family: ${pack.lighting.prompt}
- Palette: ${pack.palette.prompt}
- Character silhouette + outfit dialects stay identical every clip: ${pack.silhouette.prompt}; ${pack.outfit.prompt}
- Materials: ${pack.materialLanguage}
- Clip 1 cold-open grammar: ${pack.coldOpen}
- Clip-to-clip handoff grammar: ${pack.handoff}
- imagePrompt should mention this shot style phrase: "${pack.shotStylePhrase}" AFTER the required "While singing:" opener.
FORBIDDEN CLICHES: generic orange fox, red hoodie, empty cyclorama, identical yellow playground, "cheerful mascot on a void", voxel/Minecraft/Lego-brick blocky characters, copying the last song you generated.
${SMOOTH_CHARACTER_LOCK}
Per-clip you MAY change camera, lens, choreography verb and light ACCENT. You may NOT change art dialect, species, costume, palette family, or world geography.`;
}

export function formatClipVarietyLock(pack: SongVarietyPack, clipIndex: number): string {
  const accent = clipVarietyAccent(pack, clipIndex);
  return `CLIP ${clipIndex} ACCENT (same world, new camera/verb): camera ${accent.camera}; light accent ${accent.lightingAccent}; on-screen move: ${accent.choreo}; face emotion ${accent.emotion}.`;
}

/**
 * Look pack kilidi — SANAT LEHCESI HARIC.
 *
 * Lehce cumlesi promptun stil blogunda zaten bir kez yazilir; eskiden
 * formatStyleOverlay onu TEKRAR yaziyordu ve ayni paragraf hem [STYLE] hem
 * SHOT PLAN icinde iki kez gecip ~1.5k karakter israf ediyordu (o yuzden de
 * prompt limiti asilip [STYLE] tamamen kesiliyordu).
 */
export function formatLookPackLock(pack: SongVarietyPack, clipIndex: number): string {
  const accent = clipVarietyAccent(pack, clipIndex);
  return [
    `LOOK PACK ${pack.packId} — LOCKED FOR EVERY CLIP OF THIS SONG:`,
    `world ${pack.world.prompt}; ${pack.weather};`,
    `palette ${pack.palette.prompt};`,
    `lighting ${pack.lighting.prompt};`,
    `silhouette ${pack.silhouette.prompt}; outfit ${pack.outfit.prompt}.`,
    `THIS CLIP ONLY: camera ${accent.camera}; light accent ${accent.lightingAccent}.`,
    SMOOTH_CHARACTER_LOCK,
  ].join(" ");
}

export function formatStyleOverlay(pack: SongVarietyPack, clipIndex: number): string {
  return `PROJECT LOOK PACK ${pack.packId}: ${pack.artDialect.prompt} ${formatLookPackLock(pack, clipIndex)}`;
}

/**
 * Canli-cekim projeler icin sanat lehcesi OLMADAN suriklilik katmani:
 * dunya cografyasi, hava, palet, isik ve kamera kilitleri aile-notr kalir
 * (3D CGI cumlesi canli cekim promptuyla celisirdi).
 */
export function formatStyleOverlayNeutral(pack: SongVarietyPack, clipIndex: number): string {
  const accent = clipVarietyAccent(pack, clipIndex);
  return [
    `LOOK PACK ${pack.packId} (real, physically built version of this world) — LOCKED FOR EVERY CLIP:`,
    `location ${pack.world.prompt}; ${pack.weather};`,
    `palette ${pack.palette.prompt};`,
    `lighting ${pack.lighting.prompt};`,
    `real fabric costumes: ${pack.outfit.prompt}.`,
    `THIS CLIP ONLY: camera ${accent.camera}; light accent ${accent.lightingAccent}.`,
    "Same real location, light and costumes in every clip of this song.",
  ].join(" ");
}

export function formatLyricsContextVarietyHint(pack: SongVarietyPack): string {
  return `Sahneleme, bu projenin kilitli dunyasina otursun (${pack.world.id} / ${pack.artDialect.id} / palet ${pack.palette.id}). Jenerik sari sahne / stüdyo void yazma.`;
}

export function fallbackShotPrompt(
  pack: SongVarietyPack,
  opts: { name: string; species: string; lyrics: string; clipIndex: number }
): string {
  const accent = clipVarietyAccent(pack, opts.clipIndex);
  const lyrics = opts.lyrics.replace(/\s+/g, " ").trim().slice(0, 120);
  return `While singing: "${lyrics}". On-screen: perform the lyric meaning with visible props. ${pack.shotStylePhrase}, ${opts.name} the ${opts.species}, ${pack.silhouette.prompt}, ${pack.outfit.prompt}, in ${pack.world.prompt}, ${pack.lighting.prompt}, camera ${accent.camera}, palette ${pack.palette.prompt}.`;
}

export function stripGenericStudioLabels(text: string): string {
  return text
    .replace(/\b(3D\s+)?Pixar-style\b/gi, "stylized 3D")
    .replace(/\bPixar\s*\/\s*DreamWorks\b/gi, "theatrical family CGI")
    .replace(/\bDreamWorks\b/gi, "theatrical CGI")
    .replace(/\bPixar\b/gi, "stylized 3D");
}
