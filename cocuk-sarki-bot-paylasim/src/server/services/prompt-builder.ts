import type { CharacterProfile, Clip, Project } from "@prisma/client";
import { isKidsContent, isKidsSong } from "@/lib/templates";
import { isNarratorHardConflictGenre } from "@/lib/narrator-genres-stub";
import {
  buildStoryWordVisualLock,
  inferKidsLocationMedium,
  kidsMediumPhysicsLock,
  KIDS_FIXED_FILM_CRAFT_LOCK,
} from "@/lib/kids-prompt-stub";
import { SONG_VOICE_IDENTITY_LOCK, SONG_MV_PRODUCTION_LOCK, SONG_LYRIC_PICTURE_SYNC_LOCK, SONG_CHARACTER_FIDELITY_LOCK } from "@/lib/song-catalog";
import {
  SONG_SECOND_BY_SECOND_LOCK,
  buildSongSecondBySecondPlan,
  boostLiveActionShotPlan,
  extractSecondBySecondFull,
  extractSecondBySecondTail,
  formatSongClipBridge,
  songLipSyncLock,
  songWorldDetailFromClip,
} from "@/lib/song-prompt-craft";
import { FLOW_ANIMATED_CAST_LOCK, sanitizeKidsPromptForFlow } from "@/lib/flow-prompt-safety";
import {
  FLOW_PROMPT_MAX,
  stampNoOnscreenTextLock,
  stripEmbeddedOnscreenTextTails,
} from "@/lib/flow-prompt-compact";
import {
  formatLookPackLock,
  formatStyleOverlay,
  formatStyleOverlayNeutral,
  resolveSongVarietyPack,
  clipVarietyAccent,
  type SongVarietyPack,
} from "@/lib/song-variety";
import {
  convertShotPlanToLiveAction,
  LIVE_ACTION_SONG_REALISM,
  visualStyleFamilyOf,
  worldFamilyLock,
} from "@/lib/visual-style-family";
import {
  detectSongWorld,
  formatSongPictureConfirm,
  formatWordByWordVisualMap,
  mustShowFromAudio,
} from "@/lib/song-lyric-visual";

/**
 * Flow prompt uretimi.
 * Prompt = Ingilizce yonetmen talimatlari + secilen dilde konusma metni.
 * Sablon panelden proje bazinda duzenlenebilir (Project.promptTemplate);
 * bos ise buradaki varsayilan kullanilir.
 *
 * Sablon degiskenleri:
 * {{STYLE}} {{CHARACTER_REFERENCE}} {{SCENE_CONTINUITY}} {{CAMERA}} {{PERFORMANCE}}
 * {{VOICE}} {{LANGUAGE}} {{DIALOGUE}} {{SUBTITLES}} {{SPEECH_FIDELITY}} {{NEGATIVE}}
 * {{FLOW_CHARACTER}} {{SCENE_NOTES}} {{MUSIC}} {{LYRIC_VISUAL_LOCK}} {{DIALOGUE_VISUAL_LOCK}}
 * {{WORLD_DETAIL}} {{SECOND_BY_SECOND}} {{CHARACTER_FIDELITY}}
 */

export const DEFAULT_NARRATOR_TEMPLATE = `{{FLOW_CHARACTER}}[SPOKEN LINE — AUDIO FIRST]
She speaks this exact {{LANGUAGE}} line ON CAMERA, word for word, filling the full clip:

"{{DIALOGUE}}"

[HARD EMOTION]
{{HARD_EMOTION}}

[STYLE]
{{STYLE}}

[CHARACTER REFERENCE]
{{CHARACTER_REFERENCE}}

[SCENE CONTINUITY]
{{SCENE_CONTINUITY}}

[WORLD — FULL LOCATION]
{{WORLD_DETAIL}}

[CAMERA]
{{CAMERA}}

[PERFORMANCE]
{{PERFORMANCE}}

[AUDIO AND SPEECH]
She speaks clearly in {{LANGUAGE}}. {{SPEECH_FIDELITY}} {{VOICE}}

She says exactly (verbatim in {{LANGUAGE}} — never translate to English or any other language):

"{{DIALOGUE}}"

[ON-SCREEN TEXT]
{{SUBTITLES}}

[RESTRICTIONS]
Do not add, remove, paraphrase or translate words.
Do not add background music.
Do not add other speakers.
Keep the same adult woman — face, hair, age, wardrobe. This is the NARRATOR ON CAMERA in a lived-in home, not a studio host.
She may cry, RAISE HER VOICE, shout, swear the quoted words, slam a table, stand and sit, look away and back. Frozen beauty-ad posing and pretty melancholy are forbidden.
Do not shoot this like a commercial, catalog, perfume ad or clean talking-head product spot.
Pace the exact quoted line across the FULL clip: start in the first second, last word in the final second. Forbidden: finishing in the first 3-5 seconds then standing silent. Do not add extra words — stretch with breaths. Never cut off mid-word.
{{NEGATIVE}}`;

/**
 * Kesit plani: ekranda olay gorunur, anlatici sesi DIS SES olarak devam eder.
 * Sahnedeki kisi konusmaz; boylece anlatim butunlugu bozulmadan gorsel cesitlilik kazanilir.
 */
export const DEFAULT_CUTAWAY_TEMPLATE = `{{FLOW_CHARACTER}}[SPOKEN LINE — AUDIO FIRST]
A female narrator voice-over says this exact {{LANGUAGE}} line off screen, word for word, filling the full clip:

"{{DIALOGUE}}"

[HARD EMOTION]
{{HARD_EMOTION}}

[STYLE]
{{STYLE}}

[SHOT]
This is a fully dramatized live-action cinema scene — a real-world film take, not a talking-head, not an abstract insert, not a product shot. If a person is described below, they are physically present and actively perform the action — real blocking, real movement, real facial expression and body language, exactly like a scene from a feature film.
The female narrator is NEVER on camera. Picture shows only the story world: locations, people, props, weather and light named in the shot and in the spoken line.
{{SCENE_NOTES}}

[STORY WORD → PICTURE LOCK]
{{DIALOGUE_VISUAL_LOCK}}

[WHO IS ON SCREEN]
{{CHARACTER_REFERENCE}}

[SCENE CONTINUITY]
{{SCENE_CONTINUITY}}

[WORLD — FULL LOCATION]
{{WORLD_DETAIL}}

[CAMERA]
{{CAMERA}}

[PERFORMANCE — EMOTION IS MANDATORY]
{{PERFORMANCE}}

[AUDIO]
No one speaks on camera. This is a cinema cutaway under narration.
{{SPEECH_FIDELITY}}
A female narrator voice-over says exactly, off screen:

"{{DIALOGUE}}"

{{VOICE}}

[ON-SCREEN TEXT]
{{SUBTITLES}}

[RESTRICTIONS]
Do not add, remove, paraphrase or translate the narration.
Nobody on screen moves their lips or talks to the camera.
Do not put the narrator woman in frame (this take is a dramatized CUTAWAY under her voice-over).
Do not deliver a glossy advertisement, beauty campaign or product-ad plate — this is imperfect feature-film drama.
Do not deliver a static, frozen or empty b-roll plate: people and world must physically move and the emotion must be readable every second.
No text, no logo, no watermark.
Pace the exact narration across the FULL clip: start in the first second, last word in the final second. Forbidden: rushing the line into the first 3-5 seconds then leaving dead air. Never cut off mid-word.
{{NEGATIVE}}`;

export const DEFAULT_KIDS_TEMPLATE = `{{FLOW_CHARACTER}}[STYLE]
{{STYLE}}

[SHOT]
This is the next continuous take of ONE professionally directed 3D animated SHORT FILM (feature-quality family cinema: Pixar / DreamWorks craft) — NOT a standalone vignette and NOT a static character portrait.
Play a continuous take for the full clip duration. Follow the second-by-second action timeline in order; every second must show progress (pose, prop, gear contact, expression or blocking change). Do not freeze the same idle pose for more than one second.
MAXIMUM CLIP QUALITY: every meaningful word in the spoken story line and scene beat must be staged as tangible on-screen detail — materials, contact, consequence — never abstract mime.
{{SCENE_NOTES}}

[STORY WORD → PICTURE LOCK]
{{DIALOGUE_VISUAL_LOCK}}

[CHARACTER REFERENCE]
{{CHARACTER_REFERENCE}}
When reference images are attached in Flow, treat them as the absolute identity bible for this take.

[SCENE CONTINUITY]
{{SCENE_CONTINUITY}}

[CAMERA]
{{CAMERA}}

[PERFORMANCE]
{{PERFORMANCE}}

[PHYSICAL WORLD — ADVENTURE REALISM]
{{ADVENTURE_REALISM}}

[CINEMATIC CRAFT]
{{CINEMATIC_CRAFT}}

[AUDIO AND SPEECH]
SPEECH LANGUAGE LOCK: The character speaks ONLY in {{LANGUAGE}}. English speech, English narration and English ad-libs are FORBIDDEN unless {{LANGUAGE}} is English. Do not translate the quote.
The character speaks clearly in {{LANGUAGE}} with a warm and clear voice — crisp diction, one idea per short sentence, no mumbled or complex nested speech. {{SPEECH_FIDELITY}} {{VOICE}}

The character says exactly (verbatim in {{LANGUAGE}} — never translate):

"{{DIALOGUE}}"

Match the spoken emotion to the scene: if the line is breathless/urgent, act and speak with real adrenaline; if relieved, soft exhale in the delivery; never a flat cheerful tone that fights the words.

[ON-SCREEN TEXT]
{{SUBTITLES}}

[RESTRICTIONS]
Do not add, remove, paraphrase or translate words.
Do not add horror imagery, weapons, violence, blood or dark themes. Broadcast-safe thrilling action described in the scene (a near-miss caught by a teammate, a sudden gust, a wobbly obstacle, an exciting rescue) IS allowed and must be acted with real intensity and, where equipment is part of the story, correct gear.
Do not add other speakers than described.
Do not redesign, recolor, change identity or morph any named cast member mid-clip or between clips — locked identities only.
Do NOT reset the world between clips: same story world, same route/path continuity, same costumes with the same environment-appropriate wear, same props/setup — only the camera coverage may reframe.
Pace the exact quoted line across the FULL clip: start in the first second, last word in the final second. Forbidden: finishing in the first 3-5 seconds then standing silent with a closed mouth. Do not add extra words — stretch with natural breaths and acting pauses. Never cut off mid-word.
{{NEGATIVE}}`;

export const DEFAULT_KIDS_SONG_TEMPLATE = `{{FLOW_CHARACTER}}[SONG PICTURE CONFIRM]
{{SONG_PICTURE_CONFIRM}}

[STYLE]
{{STYLE}}

[CHARACTER FIDELITY — EVERY CLIP]
{{CHARACTER_FIDELITY}}

[CHARACTER REFERENCE]
{{CHARACTER_REFERENCE}}

[WORLD — SET / EXTERIOR / MATERIALS]
{{WORLD_DETAIL}}

[SHOT]
{{SCENE_NOTES}}

[SECOND-BY-SECOND ACTION]
{{SECOND_BY_SECOND}}

[LYRIC VISUAL LOCK]
{{LYRIC_VISUAL_LOCK}}

[SCENE CONTINUITY]
{{SCENE_CONTINUITY}}

[CAMERA]
{{CAMERA}}

[PERFORMANCE]
{{PERFORMANCE}}

[MV CRAFT]
{{CINEMATIC_CRAFT}}

[AUDIO]
EXTERNAL MASTER TRACK — NO GENERATED SINGING AUDIO IN THIS CLIP.
The final video uses a pre-mixed Suno song; this clip is VIDEO ONLY (Flow audio OFF).
Character lip-syncs / mimes to the quoted lyric for visual sync — mouth shapes match syllables but NO voice is generated here.
{{SPEECH_FIDELITY}}
{{MUSIC}}

Lyric line for lip-sync reference (not spoken by Flow): "{{DIALOGUE}}"

{{VOICE}}

[ON-SCREEN TEXT]
{{SUBTITLES}}

[RESTRICTIONS]
Do not generate singing voice, humming, or instrumental bed — silent video output.
Do not add scary imagery, weapons, violence or dark themes.
CHARACTER FIRST: keep the performer 100% on-model every frame — same face, species, height, proportions, costume colors/materials.
Perform the lyric visually across the FULL clip: last syllable pose in the final second.
COMPREHENSIVE AUDIO→PICTURE: every content word heard in this clip (sung OR spoken) must be physically visible in THIS clip — animals, objects, places, colors, numbers, verbs. Example: if the audio says a butterfly flies, a butterfly with beating wings is airborne NOW.
Do not deliver a static talking-head — real animated music video with body groove, living depth, sky/ground, and beat-alive background extras.
No sliding feet, morphing faces, warped limbs, flicker redesigns, twin duplicates or empty sparse sets.
{{NEGATIVE}}`;

/**
 * Gorsel stil on ayarlari. Panel bu anahtarlari gosterir; deger olarak
 * Ingilizce yonetmen tarifi prompta yazilir. Kullanici serbest metin de girebilir.
 */
export const VISUAL_STYLE_PRESETS: Array<{ id: string; label: string; prompt: string; recommendedFor: "narrator" | "kids" | "both" }> = [
  {
    id: "photorealistic",
    label: "Gercekci (canli cekim)",
    prompt:
      "Photorealistic LIVE-ACTION footage on a full-frame cinema camera with prime lenses — indistinguishable from real footage, never rendered. OPTICS: true optical depth of field, creamy natural bokeh, motion blur tied to shutter angle, faint edge chromatic aberration, real sensor grain. LIGHT: every source physically motivated (sun, sky, practicals, bounce) — one consistent direction, correct softness and falloff, accurate colour temperature, volumetric haze and drifting dust in shafts, true bounce colour between surfaces. SURFACES: skin with pores, vellus hair, oil sheen, asymmetry and blood flush; wet eyes with iris fibre detail and the environment mirrored in the cornea; hair as individual strands; fabric weave, stitching, wrinkles that follow the pose and wear at stress points; wood grain, metal micro-scratches, glass refraction, water beading with real surface tension. SET: lived-in locations with genuine dust, chips, clutter and age — nothing looks freshly modelled. GRADE: filmic contrast, deep detailed blacks, clean highlights. BANNED: cartoon, CGI, 3D render, illustration, plastic skin, airbrushed retouching, waxy faces.",
    recommendedFor: "narrator",
  },
  {
    id: "cinematic",
    label: "Sinematik film gorunumu",
    prompt:
      "Cinematic feature-film photography: 35mm anamorphic-leaning lens character with subtle horizontal flares and oval bokeh, dramatic but always MOTIVATED lighting — every key, rim and practical is visible or implied inside the scene. Gentle halation blooming around hot highlights, fine organic film grain, rich filmic contrast curve with deep detailed blacks and clean rolled-off highlights, restrained teal-amber separation between skin and background. PRODUCTION DESIGN in every frame: layered foreground, midground and background with real parallax; atmosphere (haze, smoke, steam, dust) carving depth between the layers; textured real materials in every plane. CAMERA: composed blocking with one motivated move at most (slow push, drift or handheld breath) — deliberate framing, never a random snapshot. Human detail survives the grade: skin texture, eye catchlights, individual hair strands, fabric weave. BANNED: flat commercial lighting, beauty-ad skin, catalog staging, unmotivated coloured gels, cartoon or CGI look.",
    recommendedFor: "narrator",
  },
  {
    id: "documentary",
    label: "Belgesel gorunumu",
    prompt:
      "Documentary realism: natural available light with honest color, believable imperfection — slight handheld sway, practical light sources, lived-in locations with authentic wear, dust and clutter. True-to-life skin tones and textures, real fabric creases, unstaged atmosphere. The frame reads like award-winning observational documentary footage, not a styled commercial.",
    recommendedFor: "narrator",
  },
  {
    id: "pixar3d",
    label: "3D Animasyon (Pixar tarzi)",
    prompt:
      "Feature-quality theatrical 3D CGI animation rendered like a cinema still — NOT live-action, NOT 2D, NOT stop-motion. SHADING: physically based materials with real roughness and specular response, subsurface scattering in ears, noses, paws and petals, individually groomed fur and hair strands that catch rim light and react to wind, cloth simulation with weave, seams, stitching and follow-through. EYES: wet living eyes with iris fibre detail, layered catchlights reflecting the actual set, moist lids, natural blinks and micro-saccades — never dead doll eyes. LIGHT: soft global illumination with warm coloured bounce from the real nearby surfaces, motivated key and rim, volumetric god-rays with floating dust or pollen, true contact shadows and ambient occlusion grounding every foot and prop. CAMERA: cinematic shallow depth of field with backgrounds that stay readable and detailed, motion blur on fast moves, lens-accurate perspective. SETS: multi-layer inhabited art direction — foreground props with thickness, a real floor, a deep background with architecture or landscape and living background motion; ultra-detailed prop, food and fabric textures. ACTING: faces carry genuine emotional performance in brows, cheeks and eyes with squash-and-stretch weight — never stiff plastic dolls. BANNED: flat cartoon shading, untextured plastic blobs, empty void backgrounds, blocky/voxel bodies, photographic humans.",
    recommendedFor: "kids",
  },
  {
    id: "anime",
    label: "2D Anime",
    prompt:
      "2D anime style: clean confident line art, expressive large eyes with layered iris highlights and reflections, vibrant cel-shaded colors with soft gradient lighting, detailed painted backgrounds with atmospheric perspective and depth, wind-reactive hair and clothing, smooth fluid character animation with strong key poses.",
    recommendedFor: "both",
  },
];

/**
 * Fiziksel gerceklik katmani: her klip promptunun [STYLE] blogunun sonuna
 * eklenir. Amac, gercek gozun gordugu HER SEYIN dogru islenmesi — bu bir
 * "guzel gorunsun" listesi degil, bir FIZIK dogrulama listesidir. Ornek:
 * yolda yuruyen bir adamin golgesi ayaklarina yapisik kalir, sahnedeki TUM
 * diger golgelerle ayni isik yonunu/rengini paylasir ve adimla birlikte
 * hareket eder. Ayni titizlik yansima, malzeme, atmosfer, kamera fizigi,
 * zemin etkilesimi ve insan biyomekanigi icin de gecerli.
 */
const LIVE_ACTION_REALISM = [
  "True physical realism in every visible detail — render everything exactly as a human eye (and a real camera sensor) would capture it, down to the smallest element. This is a physics checklist, not a mood board: nothing is exempt.",
  "SHADOWS (single consistent light source): every person, object and limb casts a shadow with the correct angle, length and softness for one implied light source/time of day — ALL shadows in the frame point the same direction and share the same color temperature. A person walking casts a moving shadow that stays glued to their feet and swings naturally with each stride; shadows shorten/soften with distance from the contact point and sharpen close to the ground-contact.",
  "REFLECTIONS: every reflective surface in frame (mirrors, windows, puddles, wet asphalt, polished metal, glossy floors, glass, screens, eyes, sunglasses) reflects the ACTUAL scene contents — including the people in it — with correct position, perspective, scale and motion; a person walking past a mirror or over a puddle is reflected accurately and the reflection moves in lockstep with them.",
  "LIGHT PHYSICS: bounce light carries the correct color between nearby surfaces (a red wall tints a nearby white shirt slightly); volumetric haze and visible dust/pollen motes drift through light shafts; highlights roll off naturally and clip only where a real sensor would clip; color temperature stays consistent between all light sources in one shot (warm tungsten vs cool daylight never mix by accident).",
  "MOTION PHYSICS: walking/running shows correct weight transfer, hip and shoulder counter-rotation, and heel-to-toe foot placement; clothing, hair, jewelry and loose straps follow through and settle a beat AFTER the body stops moving, never snapping instantly into place; fast motion carries natural motion blur proportional to speed, static objects show none.",
  "GROUND & ENVIRONMENT INTERACTION: feet, tires and objects leave physically correct marks in soft ground (dust puffs on dry dirt, splashes and ripples on wet pavement, compressing tracks in sand/snow/mud/tall grass that spring back slowly after); wind moves hair, loose fabric, grass, leaves and dust consistently in ONE direction and strength across the whole frame; steam/condensation forms on cold drinks or cold breath in cold air, on hot surfaces in humid heat.",
  "CAMERA & LENS BEHAVIOR: true optical depth of field with correct falloff for the stated focal length/distance; parallax between foreground, midground and background is correct and consistent during any camera move; natural sensor characteristics — subtle grain, faint chromatic aberration only at extreme frame edges, no digital plastic smoothing.",
  "SCALE, PERSPECTIVE & OCCLUSION: every object's size is correct relative to the human body and to every other object; perspective lines converge to the correct vanishing points; nearer objects correctly occlude farther ones with no z-fighting, clipping or floating geometry.",
  "HUMAN DETAIL & BIOMECHANICS: skin shows pores, fine vellus hair and natural asymmetry/imperfections; eyes are moist with visible iris texture and environment catchlights, and blink and move with natural, non-robotic saccades; hair reads as individual strands reacting to wind and motion; hands are anatomically correct with five fingers and a believable grip on anything they hold; joints articulate correctly under the body's actual pose and weight; breath is visible in cold air; sweat/skin sheen appears under real exertion or heat.",
  "MATERIALS: fabric shows weave, stitching, wrinkles that follow the body's pose, and wear at stress points; wood shows grain; metal shows scratches, smudges and correct specular highlights; glass refracts and shows thickness at its edges; water droplets bead, run and drip with real surface tension and gravity; every material's weight and stiffness reads correctly in how it moves.",
  "AUDIO-COHERENT VISUALS: mouth shapes match every spoken syllable exactly; footstep visual weight matches the implied cadence; any impact, contact or collision shows an instantly matching physical reaction (dust puff, ripple, flinch, follow-through) — nothing reacts a frame too late or not at all.",
  "Nothing looks plastic, painted, warped, morphed, mirrored-duplicate or artificial at any single moment of the clip — if in doubt, default to how a real unedited camera would record it.",
].join(" ");

/** Reklam / katalog / parfum estetiğini ezer — sinema dramasi. */
export const FEATURE_DRAMA_LOOK = [
  "FEATURE-FILM DRAMA LOOK — NOT A COMMERCIAL, NOT A BEAUTY AD, NOT A PERFUME SPOT, NOT A HOTEL BROCHURE:",
  "No glossy advertising lighting, no beauty-campaign skin, no catalog smile, no product-ad composition, no perfectly styled empty interiors.",
  "Imperfect lived-in cinema: motivated practical lamps, mixed color temperatures, visible grain, slight handheld breath, real mess on tables, tired eyes, smudged makeup, wet tears (not sparkly), rumpled clothes.",
  "When the betrayed person is on screen they may CRY (wet cheeks, shaking breath, running mascara), SHOUT (open mouth, neck strain, slamming a door or table — no graphic violence), collapse into a chair, cover their face. A pretty still pose is forbidden.",
].join(" ");

const ANIMATED_REALISM = [
  "World-class theatrical 3D CGI fidelity — every frame must hold a close frame-by-frame look like a cinema still from a feature film.",
  "Physically based materials matched to whatever surfaces actually appear in THIS scene: correct specular response for wet/dry/metal/fabric/organic surfaces, fabric weave and ripples, reflective surfaces (water, glass, metal, eyes) mirroring the environment AND the cast accurately.",
  "Fur and hair are individually groomed strands that react to wind or water; fabric shows weave, stitching and wear appropriate to the scene's own environment; loose debris that fits the scene (dust, sand, spray, leaves, snow — whichever is actually present) scatters believably on contact.",
  "Eyes wet and alive with iris detail and catchlights; breath vapor in cold air OR material sheen in heat/exertion — whichever matches THIS scene's real climate and action.",
  "Soft contact shadows ground every foot and prop, all sharing ONE consistent light direction and color across the frame; bounce light from the scene's dominant nearby surface (snow, sand, water, foliage, walls) carries its color into faces; volumetric light shafts through the scene's natural atmosphere (dust, spray, pollen, mist).",
  "Every prop has believable thickness and weight and never floats or clips through geometry; silhouettes never warp between frames.",
].join(" ");

/** 2D anime secildiginde: canli-cekim fizigi veya 3D CGI malzeme dili YAZILMAZ — celiski yaratir. */
const ANIME_STYLE_CONSISTENCY = [
  "World-class 2D anime production fidelity — every frame reads like a key frame from a theatrical anime film. NOT 3D CGI, NOT live-action, NOT photoreal — never add skin-pore or camera-sensor realism here.",
  "Consistent clean line art weight and flat cel-shading throughout the whole clip; shadow shapes are stylized hard-edged anime cel shadows (not soft photographic gradients), always cast from ONE consistent light direction shared by every character and prop in the frame.",
  "Detailed painted backgrounds matching the characters' line/color style, with the same atmospheric perspective and palette from the first frame to the last — no photographic textures bleeding into the art.",
  "Hair, clothing and scarves flow with stylized wind physics that stay consistent in direction and intensity across the shot; eyes keep the same iris highlight pattern, size and proportions in every frame.",
  "Motion stays fluid with strong key poses, using smears/speed-lines only on fast action beats — never live-action motion blur, never global-illumination bounce light, never photographic skin texture.",
].join(" ");

type StyleFamily = "live-action" | "cgi3d" | "anime2d";

/** Bir on ayarin (id ile) ait oldugu gorsel aile — gerceklik katmani BUNA gore secilir. */
function styleFamilyOfPreset(presetId: string): StyleFamily {
  if (presetId === "anime") return "anime2d";
  if (presetId === "pixar3d") return "cgi3d";
  return "live-action"; // photorealistic / cinematic / documentary
}

/**
 * Serbest metin stil icin aile tahmini + sablon turune gore varsayilan.
 * Onemli: yanlis aile secilirse celiskili prompt olusur (or. anime + "skin pores").
 */
function resolveStyleFamily(templateType: string, customText: string | undefined, presetId: string | undefined): StyleFamily {
  if (presetId) return styleFamilyOfPreset(presetId);
  if (customText && /anime|manga|2d\s*cartoon|toon(?!ed)/i.test(customText)) return "anime2d";
  if (customText && /3d|pixar|cgi|animat/i.test(customText)) return "cgi3d";
  return isKidsContent(templateType) ? "cgi3d" : "live-action";
}

/** Gorsel aileye uygun fiziksel/stilistik tutarlilik katmanini dondurur. */
function realismBlockForFamily(family: StyleFamily): string {
  if (family === "anime2d") return ANIME_STYLE_CONSISTENCY;
  if (family === "cgi3d") return ANIMATED_REALISM;
  return LIVE_ACTION_REALISM;
}

/** Sablon turune gore varsayilan stil tarifi. */
export function defaultStyleFor(templateType: string): string {
  return templateType === "kids_animation" || templateType === "kids_song"
    ? VISUAL_STYLE_PRESETS.find((p) => p.id === "pixar3d")!.prompt
    : VISUAL_STYLE_PRESETS.find((p) => p.id === "photorealistic")!.prompt;
}

/** Sablon turune gore varsayilan Flow prompt sablonu. */
export function defaultTemplateFor(templateType: string, shotType = "narrator"): string {
  if (templateType === "kids_song") return DEFAULT_KIDS_SONG_TEMPLATE;
  if (templateType === "kids_animation") return DEFAULT_KIDS_TEMPLATE;
  if (templateType === "narrator") {
    return shotType === "narrator" ? DEFAULT_NARRATOR_TEMPLATE : DEFAULT_CUTAWAY_TEMPLATE;
  }
  if (shotType === "cutaway") return DEFAULT_CUTAWAY_TEMPLATE;
  return DEFAULT_NARRATOR_TEMPLATE;
}

export interface PromptContext {
  project: Pick<
    Project,
    | "templateType"
    | "speechLanguage"
    | "promptTemplate"
    | "useFlowCharacter"
    | "aspectRatio"
    | "visualStyle"
    | "allowSubtitles"
    | "emotionCurve"
    | "clipSeconds"
    | "useReference"
  > & {
    genre?: string | null;
    id?: string;
    createdAt?: Date | string | null;
    songSettings?: string | null;
  };
  character:
    | (Pick<
        CharacterProfile,
        | "baseAppearancePrompt"
        | "baseWardrobePrompt"
        | "baseEnvironmentPrompt"
        | "baseCameraPrompt"
        | "baseVoicePrompt"
        | "negativePrompt"
        | "flowCharacterReference"
      > & { name?: string })
    | null;
  clip: Pick<Clip, "dialogue" | "index" | "sceneDescription" | "voiceTone" | "imagePrompt" | "emotionLabel"> & {
    shotType?: string;
  };
  /** Kesit planinda sahnede gorunen kadro karakteri. */
  sceneCharacter?: Pick<CharacterProfile, "name" | "baseAppearancePrompt" | "baseWardrobePrompt" | "flowCharacterReference"> | null;
  /** Sahnedeki yan kadro (cocuk animasyonu + anlatici film) — yuz/kostum kilidi. */
  supportingCast?: Array<
    Pick<CharacterProfile, "name" | "role" | "baseAppearancePrompt" | "baseWardrobePrompt" | "flowCharacterReference" | "storyRole">
  >;
  /** Ilk klipte "onceki klip" referansi olmaz. */
  isFirstClip: boolean;
  /** Bir onceki klibin ozeti — seri sureklilik icin (dogrudan devam). */
  previousClip?: Pick<Clip, "index" | "sceneDescription" | "imagePrompt" | "dialogue" | "emotionLabel" | "voiceTone"> & {
    shotType?: string;
  } | null;
  /** Sabit sefer ekipmani kilidi (renk/malzeme) — klipler arasi bozulmasin. */
  storyGearLock?: string;
}

/** Sinema anlatici: cutaway = olay sahnesi (anlatici yok); shotType "narrator" = kadin kameraya anlatir. */
function isCutaway(ctx: PromptContext): boolean {
  if (ctx.project.templateType !== "narrator") return ctx.clip.shotType === "cutaway";
  return ctx.clip.shotType !== "narrator";
}

function trySongVariety(ctx: PromptContext): SongVarietyPack | null {
  if (!isKidsSong(ctx.project.templateType)) return null;
  if (!ctx.project.id && !ctx.project.emotionCurve && !ctx.project.songSettings) return null;
  return resolveSongVarietyPack({
    id: ctx.project.id || "prompt-anon",
    createdAt: ctx.project.createdAt,
    songSettings: ctx.project.songSettings,
    emotionCurve: ctx.project.emotionCurve,
  });
}

/**
 * Gorsel stil: cocuk sablonlarinda her zaman theatrical 3D/anime ailesi
 * zorlanir; narrator stilleri serbesttir. Gerceklik/tutarlilik katmani
 * SECILEN AILEYE gore secilir (canli-cekim / 3D CGI / 2D anime) — yanlis
 * aile secilirse celiskili prompt olusur (or. anime + "skin pores").
 */
function styleBlock(ctx: PromptContext): string {
  const custom = ctx.project.visualStyle?.trim();
  const preset = custom ? VISUAL_STYLE_PRESETS.find((p) => p.id === custom) : undefined;

  // Cocuk: SECILEN AILE dunyayi belirler. "Gercekci canli cekim" secildiyse
  // 3D'ye cevrilmez — tum dunya gercek cekim olarak kilitlenir. 3D/anime
  // secildiyse her oge o ailede kalir (worldFamilyLock karisimi keser).
  if (isKidsContent(ctx.project.templateType)) {
    const kidsFamily = visualStyleFamilyOf(ctx.project.templateType, custom);
    const pack = trySongVariety(ctx);
    if (kidsFamily === "live-action") {
      const liveBase = preset ? preset.prompt : custom || VISUAL_STYLE_PRESETS.find((p) => p.id === "photorealistic")!.prompt;
      const overlay = pack ? ` ${formatStyleOverlayNeutral(pack, ctx.clip.index)}` : "";
      return `${liveBase}${overlay} ${realismBlockForFamily("live-action")} ${worldFamilyLock("live-action")}`;
    }
    const kidsPreset = preset && preset.recommendedFor !== "narrator" ? preset : undefined;
    const kidsBase = kidsPreset ? kidsPreset.prompt : defaultStyleFor(ctx.project.templateType);
    const freeform3d = custom && !preset && /3d|pixar|cgi|animat/i.test(custom) ? custom : null;
    const family: StyleFamily = kidsFamily === "anime2d" ? "anime2d" : kidsPreset ? styleFamilyOfPreset(kidsPreset.id) : "cgi3d";
    if (pack && family !== "anime2d") {
      return `${pack.artDialect.prompt} ${formatStyleOverlay(pack, ctx.clip.index)} ${realismBlockForFamily("cgi3d")} ${worldFamilyLock("cgi3d")}`;
    }
    return `${freeform3d || kidsBase} ${realismBlockForFamily(family)} ${worldFamilyLock(family)}`;
  }

  const base = !custom ? defaultStyleFor(ctx.project.templateType) : preset ? preset.prompt : custom;
  const family = resolveStyleFamily(ctx.project.templateType, custom, preset?.id);
  const drama = ctx.project.templateType === "narrator" ? ` ${FEATURE_DRAMA_LOOK}` : "";
  const hardVisual =
    ctx.project.templateType === "narrator" && isNarratorHardConflictGenre(ctx.project.genre)
      ? " HARD CONFLICT PICTURE: not a melancholic postcard. Faces shout, slam, jab, rage-cry (ugly, not pretty). Clenched jaw, neck strain, slammed doors/tables/phones. Soft sad posing is FORBIDDEN."
      : "";
  return `${base} ${realismBlockForFamily(family)}${drama}${hardVisual}`;
}

/**
 * Altyazi / ekran yazisi kontrolu.
 * Veo siklikla yanlis dilde veya kendiliginden altyazi basar; kapaliyken
 * yasak tekrarlanir ve prompt sonuna da sert kilit eklenir.
 */
function subtitlesBlock(_ctx: PromptContext): string {
  return [
    "HARD BAN — NO TEXT IN FRAME (NON-NEGOTIABLE):",
    "This exact rule is identical on EVERY clip of this film — clip 1 through clip 1000.",
    "The user did not request burned-in subtitles. Do not invent captions.",
    "This video must contain absolutely NO on-screen text of any kind for the entire duration — not even one letter.",
    "Applies to EVERY aspect ratio (9:16 vertical AND 16:9 horizontal) and EVERY template.",
    "FORBIDDEN ZONES: no text on the TOP of the frame, no text on the BOTTOM of the frame, no left/right/center banners, no YouTube caption bar, no karaoke strip, no ticker.",
    "Forbidden: subtitles, captions, closed captions, burned-in dialogue, karaoke lyrics, lyric overlays, sing-along text, lower-thirds, titles, end cards, chapter cards, speech bubbles, labels, clothing tags, apron writing, chalkboard letters, menus with words, watermarks, logos, timestamps, UI, readable signs, posters with letters, books with readable words, letter-like glyphs, OCR-looking marks.",
    "Do not write sung or spoken words onto costume, props, or the frame (no 'let's go', no lyric stickers).",
    "Forbidden in EVERY language including Turkish, English, Arabic, Chinese, and any invented alphabet.",
    "Do NOT auto-caption speech or singing. Omni/Veo often defaults to English captions — OVERRIDE that default completely.",
    "Audio may be heard; the picture stays a clean cinematic plate with zero typography.",
  ].join(" ");
}

/** Prompt sonuna yapisan son altyazi kilidi (Veo genelde son satirlara daha cok uyar). */
function subtitlesEndLock(_ctx: PromptContext): string {
  return [
    "[FINAL HARD LOCK — ON-SCREEN TEXT]",
    "FINAL CHECK BEFORE RENDER: zero subtitles, zero captions, zero karaoke, zero written words anywhere in the frame, any language — including English auto-captions.",
    "Especially: NOTHING written at the top of the picture and NOTHING written at the bottom of the picture.",
    "9:16 and 16:9: same ban. Same rule as clip 1. Reject any output that shows burned-in text. Picture only.",
  ].join(" ");
}

/**
 * Soz / sarki sadakati: duyulan ses, dudak hareketi ve yazili diyalog/soz
 * birebir ayni olsun (anlatici, cocuk hikaye, cocuk sarki).
 */
/**
 * Aldatma / yasak ask / ihanet: hüzünlü fısıltı değil.
 * Bloğu kisa tut — Flow compact'ta SPOKEN LINE'dan hemen sonra kalır.
 */
function hardEmotionBlock(ctx: PromptContext): string {
  if (ctx.project.templateType !== "narrator") return "";
  if (!isNarratorHardConflictGenre(ctx.project.genre)) {
    return "Play the real emotion of the spoken line in face, voice and body — not a pretty still.";
  }
  const onCam = !isCutaway(ctx);
  return [
    "HARD CONFLICT — NOT MELANCHOLY:",
    onCam
      ? "She is ANGRY, not a sad poem. Shout, spit the line, slam a table, jab a finger, rage-cry (ugly wet face, not pretty tears). Soft whisper-host energy is FORBIDDEN."
      : "People on screen play a FIGHT, not a rainy postcard: shout, slam a door/phone/cup, aggressive proximity, clenched jaw. Pretty frozen sadness is FORBIDDEN.",
    "If the quoted Turkish line contains swearing, those exact words are SHOUTED with matching mouth shapes — never mumbled away, never skipped.",
    ctx.clip.emotionLabel?.trim() ? `This take's heat: ${ctx.clip.emotionLabel.trim()}.` : "",
  ]
    .filter(Boolean)
    .join(" ");
}

/** Konusma, klip suresine orantili dolsun (8 sn sahnede 3-5 sn sessizlik YASAK). */
export function clipSpeechPaceLock(clipSeconds: number): string {
  const seconds = Math.max(4, Math.min(20, Math.round(clipSeconds) || 8));
  return [
    `SPEECH PACING LOCK — ${seconds}s CLIP:`,
    `Spoken audio must fill this ${seconds}-second take, proportional to clip length.`,
    `Start speaking in the first second; the LAST quoted word lands in the final 1 second.`,
    `Forbidden: rushing the line into the first 3-5 seconds, then standing silent with a closed mouth.`,
    `Do not invent extra words — stretch the EXACT quote with natural breaths, acting pauses and clear diction so speech lasts ~${seconds}s.`,
    `The last word still completes inside the clip — never cut off mid-word.`,
  ].join(" ");
}

function speechFidelityBlock(ctx: PromptContext): string {
  const lang = ctx.project.speechLanguage;
  const seconds = Math.max(4, Math.min(20, ctx.project.clipSeconds || 8));
  if (isKidsSong(ctx.project.templateType)) {
    return [
      "LYRIC VISUAL SYNC — NON-NEGOTIABLE (SILENT CLIP — NO FLOW AUDIO):",
      `Mouth shapes / visemes must match the quoted ${lang} lyric syllables as if lip-syncing to an external master track.`,
      "Do NOT generate singing voice, speech, humming or music bed — this export is video-only.",
      "Picture and performance must sell the SAME lyric meaning: every content word (noun, verb, color, number, spoken aside) appears as the line would be heard.",
      "COMPREHENSIVE: skip none — if the audio says a butterfly flies, a butterfly is airborne in THIS clip.",
      `Perform the lyric visually across the full ${seconds}s — last syllable pose in the final second.`,
    ].join(" ");
  }
  if (isCutaway(ctx)) {
    return [
      "NARRATION FIDELITY — NON-NEGOTIABLE:",
      `The off-screen narrator says ONLY the exact quoted lines in ${lang}, word for word.`,
      "No added phrases, no translation, no paraphrase. On-screen talent stays silent — no speaking lip movement.",
      clipSpeechPaceLock(seconds),
    ].join(" ");
  }
  return [
    "SPEECH FIDELITY — NON-NEGOTIABLE:",
    `Speak ONLY the exact quoted lines in ${lang}, word for word, in order. This is SPOKEN dialogue, not singing.`,
    `AUDIO LANGUAGE: ${lang} only. Do NOT speak English (or any other language) unless ${lang} itself is English.`,
    "Mouth shapes / visemes must match every spoken syllable of that audio (accurate lip-sync to the quoted line).",
    "Do not add, skip, reorder, paraphrase or translate words. Do not switch language mid-line. Do not hum or sing.",
    "Crisp diction first so each word is intelligible; emotional tone follows the line meaning.",
    clipSpeechPaceLock(seconds),
  ].join(" ");
}

function characterFidelityBlock(ctx: PromptContext): string {
  if (!isKidsSong(ctx.project.templateType)) return "";
  const c = ctx.character;
  const support = (ctx.supportingCast ?? [])
    .filter((m) => m.name?.trim())
    .slice(0, 6)
    .map((m) => {
      const look = [m.baseAppearancePrompt, m.baseWardrobePrompt].filter(Boolean).join(" / ").replace(/\s+/g, " ").trim();
      return look ? `${m.name}: ${look.slice(0, 160)}` : m.name;
    });
  const bits = [
    SONG_CHARACTER_FIDELITY_LOCK,
    c?.name?.trim() ? `Locked lead singer this entire song: ${c.name.trim()}.` : "",
    c?.baseAppearancePrompt?.trim()
      ? `FULL written face/species/body/HEIGHT lock (repeat every clip): ${c.baseAppearancePrompt.trim()}`
      : "",
    c?.baseWardrobePrompt?.trim()
      ? `Costume identical head-to-toe (colors + materials + accessories): ${c.baseWardrobePrompt.trim()}`
      : "",
    c?.baseEnvironmentPrompt?.trim()
      ? `Home-set reminder (do not teleport away unless lyric demands): ${c.baseEnvironmentPrompt.trim().slice(0, 180)}`
      : "",
    support.length ? `Supporting cast locks (do not redesign): ${support.join(" | ")}` : "",
    "If a lyric prop, camera move or background flourish would change the singer's face, species, height or costume — DROP the flourish and keep the singer correct.",
  ];
  return bits.filter(Boolean).join(" ");
}

function characterReferenceBlock(ctx: PromptContext): string {
  const c = ctx.character;
  const refActive = !!ctx.project.useReference;
  const hardLock = refActive
    ? ctx.project.templateType === "kids_animation"
      ? [
          "UPLOADED REFERENCE IMAGE(S) = FRONT+BACK TURNAROUND SHEETS for FACE / SPECIES / BODY identity.",
          "Each sheet shows ONE character twice: LEFT=front, RIGHT=back — not two different people.",
          "Every frame must match those references 1:1 for face shape, eye color, species/silhouette, fur/hair pattern, HEIGHT and body proportions.",
          "COSTUME FOR THIS FILM: follow the written Costume lock and STORY PROP / GEAR LOCK of THIS story only.",
          "If the reference sheet shows a different outfit from a previous adventure (e.g. mountain/Everest gear while THIS story is sea/yacht/dive), IGNORE that old clothing — keep only face/species/body from the reference and dress the hero for THIS story.",
          "Do NOT invent a new species, recolor the fur/surface palette, change identity, morph body proportions or ignore the written wardrobe of this film.",
        ].join(" ")
      : [
          "UPLOADED REFERENCE IMAGE(S) = FRONT+BACK TURNAROUND SHEETS (ground-truth identity).",
          "Each sheet shows ONE character twice: LEFT=front, RIGHT=back — not two different people.",
          "Every frame must match those references 1:1 for face shape, eye color, species/silhouette, fur/hair pattern, costume colors, accessories, HEIGHT and body proportions.",
          "Do NOT invent a new design, recolor palette, change identity, morph species or swap outfits.",
          "If the model drifts even slightly from a reference, prefer the reference over any other description.",
        ].join(" ")
    : "";

  if (isCutaway(ctx)) {
    const onScreen: NonNullable<PromptContext["supportingCast"]> = [];
    const pushPerson = (
      person:
        | PromptContext["sceneCharacter"]
        | NonNullable<PromptContext["supportingCast"]>[number]
        | null
        | undefined
    ) => {
      const name = person?.name?.trim();
      if (!person || !name) return;
      if (onScreen.some((x) => x.name.trim().toLowerCase() === name.toLowerCase())) return;
      onScreen.push({
        name,
        role: "role" in person && person.role ? person.role : "side",
        storyRole: "storyRole" in person ? person.storyRole || "" : "",
        baseAppearancePrompt: person.baseAppearancePrompt,
        baseWardrobePrompt: person.baseWardrobePrompt,
        flowCharacterReference: person.flowCharacterReference,
      });
    };
    pushPerson(ctx.sceneCharacter);
    for (const member of ctx.supportingCast ?? []) pushPerson(member);

    if (onScreen.length === 0) {
      return [
        "No recognizable person is featured; if a figure appears, keep them distant, out of focus or seen from behind.",
        "Do not invent a new recurring face or morph extras into a named character.",
        "The narrator is NOT in this shot.",
      ].join(" ");
    }

    const parts = [
      hardLock,
      "ONLY the locked identities below may have a readable face. Do not invent extras, twins, or a second version of anyone. Do not morph one face into another.",
    ];
    for (const person of onScreen) {
      const flowRef = person.flowCharacterReference?.trim();
      parts.push(
        [
          flowRef ? `${flowRef} appears in this shot.` : "",
          `On screen: ${person.name}. ${person.baseAppearancePrompt || ""}`.trim(),
          person.baseWardrobePrompt ? `Wardrobe: ${person.baseWardrobePrompt}` : "",
          `Keep ${person.name} identical every time they appear: same face, gender, age, hair and outfit.`,
        ]
          .filter(Boolean)
          .join(" ")
      );
    }
    parts.push("The narrator herself is NOT in this shot.");
    return parts.filter(Boolean).join(" ");
  }
  if (ctx.project.templateType === "narrator") {
    const parts: string[] = [];
    if (hardLock) parts.push(hardLock);
    parts.push(
      "This woman is the NARRATOR ON CAMERA — the cheated-on / storyteller in a lived-in home, not a studio host, not a beauty model."
    );
    parts.push(
      "Use the exact same adult woman from the supplied character reference. Preserve exactly the same face, age, height, hairstyle, hair color, skin tone, body proportions and wardrobe."
    );
    parts.push(
      "Lived-in look: tired eyes, possible wet tears, smudged makeup, rumpled clothes. Beauty-campaign glamour, catalog smile and perfume-ad skin are forbidden."
    );
    if (c?.baseAppearancePrompt) parts.push(c.baseAppearancePrompt);
    if (c?.baseWardrobePrompt) parts.push(`Wardrobe: ${c.baseWardrobePrompt}`);
    return parts.join(" ");
  }
  if (isKidsSong(ctx.project.templateType)) {
    const parts: string[] = [
      hardLock,
      SONG_CHARACTER_FIDELITY_LOCK,
      "Match the supplied character reference / turnaround EXACTLY: same face, species, fur/surface pattern, eye color, HEIGHT, body proportions and costume. 3D animated character, not live-action.",
      "Character consistency is TOP PRIORITY for this music video — higher than camera flourish, background density or dance energy.",
      "EVEN WITH a reference image attached: ALWAYS restate FULL written face, species, colors, HEIGHT, proportions, costume head-to-toe and signature prop. Reference reinforces; it never replaces the written lock.",
      "Height and proportions are FIXED for the whole song — never grow, shrink, age or slim between clips.",
    ];
    if (c?.name?.trim()) parts.push(`Lead singer name lock: ${c.name.trim()}.`);
    if (c?.baseAppearancePrompt?.trim()) {
      parts.push(`FULL appearance lock (repeat every clip): ${c.baseAppearancePrompt.trim()}`);
    }
    if (c?.baseWardrobePrompt?.trim()) {
      parts.push(`Costume lock (identical every clip): ${c.baseWardrobePrompt.trim()}`);
    }
    parts.push(
      "If the face/body starts to drift from the lock, STOP the drift — prefer the locked design over any new detail."
    );
    return parts.filter(Boolean).join(" ");
  }
  if (ctx.project.templateType === "kids_animation") {
    const parts: string[] = [
      hardLock,
      "Match the supplied character reference image(s) for the HERO and every supporting cast member on screen: same face, species, colors, HEIGHT and body proportions. 3D animated characters, not live-action.",
      "Character consistency is TOP PRIORITY — higher than camera flourish or background detail.",
      "EVEN WITH reference / turnaround image(s) attached: ALWAYS restate FULL written face, species, fur/surface colors, eye color, HEIGHT, body proportions/head-to-body ratio, costume head-to-toe and signature props. Written Costume lock for THIS film wins over any older outfit visible on a reused reference sheet.",
      "Height and proportions are FIXED constants decided once at character creation — the hero and every named cast member stay the exact same height/build in every single clip of the film, no growing, shrinking, aging or slimming.",
    ].filter(Boolean) as string[];
    if (c?.baseAppearancePrompt) parts.push(`Hero FULL lock: ${c.baseAppearancePrompt}`);
    if (c?.baseWardrobePrompt) parts.push(`Hero costume + any locked signature props stay the same: ${c.baseWardrobePrompt}`);
    if (ctx.storyGearLock?.trim()) {
      parts.push(`Hero/team prop colors never drift: use the STORY PROP / GEAR LOCK exactly.`);
    }
    const cast: NonNullable<PromptContext["supportingCast"]> = ctx.supportingCast?.length
      ? ctx.supportingCast
      : ctx.sceneCharacter
        ? [
            {
              name: ctx.sceneCharacter.name,
              role: "side",
              storyRole: "",
              baseAppearancePrompt: ctx.sceneCharacter.baseAppearancePrompt,
              baseWardrobePrompt: ctx.sceneCharacter.baseWardrobePrompt,
              flowCharacterReference: ctx.sceneCharacter.flowCharacterReference,
            },
          ]
        : [];
    for (const member of cast) {
      const memberName = member.name?.trim();
      if (!memberName) continue;
      if (c?.name && memberName.toLowerCase() === c.name.trim().toLowerCase()) continue;
      const flowRef = member.flowCharacterReference?.trim() || "";
      const role = member.storyRole?.trim() || (member.role === "main" ? "hero" : "supporting friend");
      parts.push(
        [
          flowRef && ctx.project.useFlowCharacter ? `${flowRef} also appears.` : "",
          `Also on screen with EXACT locked identity every time: ${memberName} (${role}).`,
          member.baseAppearancePrompt?.trim() || "",
          member.baseWardrobePrompt?.trim() ? `Their costume: ${member.baseWardrobePrompt.trim()}` : "",
          "Do not redesign, recolor or change identity of this supporting character between scenes.",
        ]
          .filter(Boolean)
          .join(" ")
      );
    }
    parts.push("Every named cast member who appears must match their locked look — never a random redesign.");
    return parts.join(" ");
  }
  const parts: string[] = [];
  if (hardLock) parts.push(hardLock);
  parts.push(
    "Use the exact same adult character from the supplied character reference. Preserve exactly the same face, age, height, hairstyle, hair color, skin tone, body proportions, makeup, outfit and accessories."
  );
  if (c?.baseAppearancePrompt) parts.push(c.baseAppearancePrompt);
  if (c?.baseWardrobePrompt) parts.push(`Wardrobe: ${c.baseWardrobePrompt}`);
  return parts.join(" ");
}

function sceneContinuityBlock(ctx: PromptContext): string {
  const c = ctx.character;
  const parts: string[] = [];
  if (isKidsSong(ctx.project.templateType)) {
    parts.push(
      "SERIAL FAMILY MUSIC-VIDEO CONTINUITY (NON-NEGOTIABLE): this clip is the NEXT consecutive seconds of ONE continuous music video — never a disconnected standalone music video, never a brand-new set every 8 seconds."
    );
    parts.push("Same 3D character, costume, color palette, face and body proportions as the IDENTITY LOCK — no redesign between clips.");
    parts.push(SONG_MV_PRODUCTION_LOCK);
    if (ctx.isFirstClip) {
      parts.push(
        "Establish a DENSE music-video world: deep multi-layer set (foreground props with material detail, mid-ground stage, lively readable background), rich materials, color accents, and small moving details that belong in this song's world — not a flat empty room or sparse void."
      );
      parts.push(
        "Opening MV energy: audible groove from second 0; singer already bouncing/gesturing on the beat while the living set pulses — never a frozen establishing portrait."
      );
    } else {
      const prev = ctx.previousClip;
      const prevTail = extractSecondBySecondTail(prev?.imagePrompt);
      const prevBits = [
        prev?.sceneDescription?.trim() ? `Panel beat: ${prev.sceneDescription.trim().slice(0, 180)}` : "",
        prevTail ? `LAST 1–2s TO MATCH-ON-ACTION: ${prevTail.slice(0, 220)}` : "",
        prev?.imagePrompt?.trim() && !prevTail
          ? `Visual end-state hint: ${prev.imagePrompt.trim().slice(0, 220)}`
          : "",
        prev?.dialogue?.trim() ? `Previous lyric energy still ringing: "${prev.dialogue.trim().slice(0, 100)}"` : "",
        prev?.emotionLabel?.trim() || prev?.voiceTone?.trim()
          ? `Performance hangover: ${[prev.emotionLabel, prev.voiceTone].filter(Boolean).join(" / ")}`
          : "",
      ]
        .filter(Boolean)
        .join(" | ");
      parts.push(
        "DIRECT CONTINUATION / MATCH-ON-ACTION: start mid-performance as if there was no hard cut — same MV set geography, same lighting warmth, same costume, same prop materials/positions unless THIS lyric beat explicitly introduces a new prop."
      );
      if (prevBits) parts.push(`Previous clip #${prev?.index ?? "?"} carry-over: ${prevBits}`);
      parts.push(
        "Bridge the first 0-1s from the previous last second (body still mid-bounce/gesture, mouth mid-phrase energy, feet still planted on the SAME floor, gaze still engaged) then advance ONE lyric beat — never reset the song world or teleport to a random empty set."
      );
      parts.push(
        "Camera coverage may reframe (new shot size/angle for MV variety) BUT the singer, voice identity, groove, set continuity and emotional energy must feel continuous."
      );
    }
    parts.push(
      "Background is never dead or blank: soft parallax depth, secondary motion locked to the beat (leaves, bubbles, curtains, light rays, distant toys, drifting particles), readable silhouettes behind the singer."
    );
    try {
      const meta = JSON.parse(ctx.project.emotionCurve || "{}") as { beatVisuals?: string };
      if (meta.beatVisuals?.trim()) {
        parts.push(`Style beat language for THIS song (apply every second): ${meta.beatVisuals.trim()}`);
      }
    } catch {
      /* ignore */
    }
    return parts.join(" ");
  }
  // Cocuk ANİMASYONU: TEK kisa film — her klip oncekinin DOGRUDAN devamı.
  if (ctx.project.templateType === "kids_animation") {
    // NOT: burada hicbir temaya (dag, deniz, uzay...) ozel metin YOKTUR. Ortam, prop ve
    // mekanik SADECE sahnenin kendi tanimindan ve tema prop kilidinden gelir — boylece
    // secilmeyen bir tema promptlara asla sizmaz.
    parts.push(
      "SERIAL SHORT-FILM CONTINUITY (NON-NEGOTIABLE — moral lesson AND adventure themes alike): this clip is the NEXT continuous seconds of the SAME short film — never a disconnected standalone episode or a brand-new mini-story every 8–10 seconds."
    );
    parts.push(
      "ONE STORY SPINE: same goal/route/problem across the whole film; this take advances ONE small step only — no teleport, no mid-film re-introduction, no fresh establishing of a new world."
    );
    parts.push(
      "Same 3D hero and cast: identical faces, species, costumes, color palette, and the SAME worn-in wear/dirt marks on clothes as the prior beat (whatever is appropriate for this story's own setting)."
    );
    if (ctx.isFirstClip) {
      parts.push(
        "Opening beat of the film: establish THIS story's OWN world exactly as described in the scene block — never invent a different setting, biome or activity than the one described — with deep multi-layer sets, lived-in props specific to that setting, readable backgrounds, soft global illumination; AND the hero is ALIVE on camera (speaking intro, waving, pointing to a landmark or signature prop), never a frozen establishing portrait."
      );
      parts.push(
        "HERO VISIBILITY LOCK (OPENING): the named HERO must be clearly visible as the PRIMARY on-screen subject for nearly every second — medium/close enough to read face and costume. Supporting cast may appear WITH the hero, never INSTEAD of the hero. Do not crop the hero out; do not replace the hero with only background extras or only the captain."
      );
      parts.push(
        "If this opening includes spoken greeting/plan dialogue, stage a medium talking address with clear gestures each second — mouth shapes, weight shifts, invite energy — then soft-bridge into today's adventure in this story's own setting."
      );
      const openMedium = inferKidsLocationMedium(
        [ctx.clip.sceneDescription, ctx.clip.imagePrompt, ctx.clip.dialogue].filter(Boolean).join("\n")
      );
      if (openMedium !== "UNKNOWN") parts.push(kidsMediumPhysicsLock(openMedium));
    } else {
      const prev = ctx.previousClip;
      const prevPlace = [prev?.sceneDescription, prev?.imagePrompt, prev?.dialogue].filter(Boolean).join("\n");
      const prevMedium = inferKidsLocationMedium(prevPlace);
      const thisMedium = inferKidsLocationMedium(
        [ctx.clip.sceneDescription, ctx.clip.imagePrompt, ctx.clip.dialogue].filter(Boolean).join("\n")
      );
      const prevTail = (() => {
        const ip = prev?.imagePrompt?.trim() || "";
        const m = ip.match(/Second-by-second action[\s\S]*?:\s*([\s\S]+?)(?:\n\n|Prop craft|Serial continuity|Clarity lock|Identity lock|Micro-realism|FINAL FRAME|$)/i);
        const timeline = m?.[1]?.trim() || "";
        if (!timeline) return "";
        const chunks = timeline.split(/;\s*/).map((p) => p.trim()).filter(Boolean);
        return chunks.slice(-2).join("; ");
      })();
      const prevBits = [
        prevMedium !== "UNKNOWN" ? `prev medium: ${prevMedium}` : "",
        thisMedium !== "UNKNOWN" ? `this medium: ${thisMedium}` : "",
        prev?.sceneDescription?.trim() ? `Panel beat: ${prev.sceneDescription.trim().slice(0, 180)}` : "",
        prevTail ? `LAST 1–2s TO MATCH-ON-ACTION: ${prevTail.slice(0, 220)}` : "",
        prev?.imagePrompt?.trim() && !prevTail
          ? `Visual end-state hint: ${prev.imagePrompt.trim().slice(0, 220)}`
          : "",
        prev?.emotionLabel?.trim() || prev?.voiceTone?.trim()
          ? `Emotional hangover into this take: ${[prev.emotionLabel, prev.voiceTone].filter(Boolean).join(" / ")}`
          : "",
        prev?.dialogue?.trim() ? `Last spoken line energy still in the air: "${prev.dialogue.trim().slice(0, 100)}"` : "",
      ]
        .filter(Boolean)
        .join(" | ");
      parts.push(
        "DIRECT CONTINUATION / MATCH-ON-ACTION: start mid-action as if there was no hard cut — same location/geography AND same physical MEDIUM as the previous beat (deck stays deck; underwater stays underwater), same weather/mood, same wet/dry state, same prop positions and configuration, unless this beat is an explicit TRANSITION."
      );
      if (prevBits) parts.push(`Previous clip #${prev?.index ?? "?"} carry-over: ${prevBits}`);
      if (thisMedium !== "UNKNOWN") parts.push(kidsMediumPhysicsLock(thisMedium));
      else if (prevMedium !== "UNKNOWN") parts.push(kidsMediumPhysicsLock(prevMedium));
      parts.push(
        "Bridge the first 0-1s from the previous last second (hand/body still mid-gesture, breath still visible if relevant, feet/body still contacting the SAME surface type, gaze still locked) then advance ONE small story step — never reset the conversation or teleport biomes (NO ship-deck → dry-land swimming jump)."
      );
      parts.push(
        "Camera coverage may reframe (new shot size/angle for cinema variety) BUT the world, cast, props, medium and emotional state must feel continuous — never teleport to a random new location outside this story's established setting."
      );
    }
    parts.push(
      "Backgrounds stay alive: particles/atmosphere and distant background activity as soft silhouettes, fabric/foliage/water motion appropriate to THIS scene's own setting — secondary motion every second."
    );
    parts.push(
      "LOCOMOTION LOCK: feet/body PLANT with real weight transfer for this scene's actual terrain (sand, grass, water, deck, floor, rock, etc.). Absolutely NO sliding, skating, gliding, skate-steps, floaty moonwalk or rubbery slip-travel. Maximum living realism — breath, fur/fabric/hair micro-motion, contact shadows."
    );
    parts.push(KIDS_FIXED_FILM_CRAFT_LOCK);
    return parts.join(" ");
  }
  if (ctx.project.templateType === "narrator") {
    const prev = ctx.previousClip;
    const prevWasNarrator = prev?.shotType === "narrator";
    const filmParts: string[] = [];
    if (isCutaway(ctx)) {
      filmParts.push(
        "ONE continuous live-action film: same story world, era, weather and recurring locations. This take is a CUTAWAY — the narrator woman is NOT in frame."
      );
      if (ctx.isFirstClip) {
        filmParts.push(
          "Opening cinema take: establish THIS story's real location from the SHOT block — lived-in architecture, motivated practical lights, weather and period detail. Not a studio sofa, not a talking-head interior, not a beauty commercial."
        );
      } else if (prevWasNarrator) {
        filmParts.push(
          "SOFT CUT from the narrator's confession back into the story world — pick up the beat the line is describing. Do not teleport; keep era, weather and recurring locations."
        );
      } else {
        filmParts.push(
          "DIRECT CONTINUATION / MATCH-ON-ACTION: start from the previous clip's last second — same place unless the shot explicitly moves, same weather/wet-dry, same props, then advance one story beat. Soft transition only; no teleport, no reset to a generic living room."
        );
      }
    } else {
      filmParts.push(
        "NARRATOR CONFESSION take of the SAME film: the storyteller woman is ON CAMERA in a lived-in room, speaking to camera. Imperfect feature-film drama, not a commercial, not a catalog, not a locked sofa talking-head."
      );
      if (ctx.isFirstClip) {
        filmParts.push(
          "Opening confession: establish her real room — ceiling, floor, two walls, a window with the real outside, practical lamp, mess on the table. She is already in the emotion of the first line."
        );
      } else if (!prevWasNarrator) {
        filmParts.push(
          "SOFT CUT from the dramatized story world back to the SAME confession room as other narrator takes — same woman, same wardrobe, same lived-in space."
        );
      } else {
        filmParts.push(
          "DIRECT CONTINUATION in the confession room: same woman, same seat/standing spot unless she just stood up, same lamp and mess, then the next sentence of the same confession."
        );
      }
    }
    if (!ctx.isFirstClip && prev?.sceneDescription?.trim()) {
      filmParts.push(`Previous shot to match: ${prev.sceneDescription.trim().slice(0, 220)}`);
    }
    if (!ctx.isFirstClip && prev?.imagePrompt?.trim()) {
      filmParts.push(`Previous visual lock: ${prev.imagePrompt.trim().slice(0, 180)}`);
    }
    if (ctx.clip.imagePrompt?.trim()) filmParts.push(ctx.clip.imagePrompt.trim().slice(0, 500));
    return filmParts.join(" ");
  }
  if (ctx.isFirstClip) {
    parts.push(c?.baseEnvironmentPrompt || "A consistent, well-lit indoor environment.");
  } else {
    parts.push(
      "Use the same room, chair, background, lighting, camera height, camera distance, lens appearance and framing as the previous clip."
    );
    if (c?.baseEnvironmentPrompt) parts.push(`Environment: ${c.baseEnvironmentPrompt}`);
  }
  return parts.join(" ");
}

/**
 * Anlatici: mevcut SHOT/CONTINUITY bloklarini bozmadan tam mekan katmani.
 * Ic/dis/esik her yerde tavan veya gokyuzu, zemin, derinlik ve yasayan arka plan.
 */
function extractTaggedBlock(source: string, tag: string): string {
  const re = new RegExp(`\\[${tag}\\]\\s*([^\\[]+)`, "i");
  return source.match(re)?.[1]?.replace(/\s+/g, " ").trim() || "";
}

export function narratorWorldDetailBlock(imagePrompt: string, sceneDescription: string): string {
  const visual = `${imagePrompt || ""}\n${sceneDescription || ""}`;
  const setting = extractTaggedBlock(visual, "SETTING").toLowerCase();
  const env = extractTaggedBlock(visual, "ENVIRONMENT");
  const bg = extractTaggedBlock(visual, "BACKGROUND LAYERS") || extractTaggedBlock(visual, "BACKGROUND");
  const set = extractTaggedBlock(visual, "SET DRESSING");
  const atmo = extractTaggedBlock(visual, "ATMOSPHERE");
  return [
    "ADDED PRODUCTION-DESIGN LAYER (does not replace SHOT, CAMERA, PERFORMANCE or CONTINUITY): dress THIS exact location as a complete inhabited world — never a void, never a studio cyclorama, never a cropped close-up with nothing behind the people.",
    "EXTERIOR: ground underfoot + sky or weather ceiling + horizon + real architecture or landscape in depth + distant living activity (traffic glow, other windows, trees moving, unreadable pedestrians). No empty white-sky plate.",
    "INTERIOR: ceiling, floor, at least two walls, a window or doorway that shows the real outside, furniture with wear, practical lamps, clutter that belongs to these people. The room continues off-frame.",
    "THRESHOLD (door, balcony, car, window): show BOTH an interior fragment AND the exterior world beyond.",
    "Foreground / mid-ground / background ALL readable. Materials match wet/dry, dust, paint age, glass reflecting the ACTUAL scene.",
    setting ? `Setting type this take: ${setting}.` : "",
    env ? `Environment lock: ${env}` : "",
    bg ? `Background layers: ${bg}` : "",
    set ? `Set dressing: ${set}` : "",
    atmo ? `Atmosphere: ${atmo}` : "",
  ]
    .filter(Boolean)
    .join(" ");
}

function worldDetailBlock(ctx: PromptContext): string {
  if (isKidsSong(ctx.project.templateType)) {
    const pack = trySongVariety(ctx);
    const base = songWorldDetailFromClip({
      imagePrompt: ctx.clip.imagePrompt,
      sceneDescription: ctx.clip.sceneDescription,
      isFirstClip: ctx.isFirstClip,
    });
    if (!pack) return base;
    return `${base} PROJECT WORLD LOCK (${pack.packId}): ${pack.world.prompt}. Weather: ${pack.weather}. Palette: ${pack.palette.prompt}. Do not teleport to a generic playground.`;
  }
  if (ctx.project.templateType !== "narrator") return "";
  return narratorWorldDetailBlock(ctx.clip.imagePrompt || "", ctx.clip.sceneDescription || "");
}

function secondBySecondBlock(ctx: PromptContext): string {
  if (!isKidsSong(ctx.project.templateType)) return "";
  const seconds = Math.max(4, Math.min(20, ctx.project.clipSeconds || 8));
  const fromShot = extractSecondBySecondFull(ctx.clip.imagePrompt);
  const previousTail = ctx.isFirstClip ? "" : extractSecondBySecondTail(ctx.previousClip?.imagePrompt);
  const pack = trySongVariety(ctx);
  const accent = pack ? clipVarietyAccent(pack, ctx.clip.index) : null;
  const plan =
    fromShot ||
    buildSongSecondBySecondPlan({
      lyrics: ctx.clip.dialogue || "",
      seconds,
      isFirstClip: ctx.isFirstClip,
      previousTail,
      beatVerb: accent?.beatVerb,
      coldOpen: pack?.coldOpen,
      handoff: pack?.handoff,
    });
  return [SONG_SECOND_BY_SECOND_LOCK, `TIMELINE 0-${seconds}s (hit in order): ${plan}`].join(" ");
}

function cameraBlock(ctx: PromptContext): string {
  if (isCutaway(ctx)) {
    return "Cinematic coverage of a real dramatized scene, filmed like an actual movie moment as it happens — not a talking-head, not a static insert, not a product close-up, not a beauty advertisement. Follow the camera note in the SHOT / CAMERA blocks; at most one slow motivated move. Single continuous take, no cuts.";
  }
  if (ctx.project.templateType === "narrator") {
    return "Intimate feature-film confession coverage: medium close-up of the woman in a lived-in room, motivated practical lamp, mixed color temperature, slight handheld breath. She may lean, cover her face, look away and back. Not a beauty-ad lock-off, not a fixed-tripod catalog shot. Single continuous take, no cuts.";
  }
  if (isKidsSong(ctx.project.templateType)) {
    const seconds = Math.max(4, Math.min(20, ctx.project.clipSeconds || 8));
    return [
      "Music-video camera grammar (feature CGI, broadcast-safe): follow the camera note in the SHOT block.",
      `Single continuous ${seconds}s take — no cuts, no whip pan, no handheld shake, no morph during the move.`,
      "Shot variety across the SONG (not inside one clip): medium performance, occasional 35-50mm-feel push-in on the hook, gentle beat-bob or slow push — keep full singer silhouette + headroom + deep set.",
      "Always show ground contact under feet AND sky/ceiling/horizon behind — never crop into empty void.",
      "Eyeline continuity with previous clip; parallax on a foreground lyric-prop is allowed.",
      "ANTI-GLITCH camera: stable mesh, no warping limbs, no stretchy faces, no flicker redesigns while travelling.",
    ].join(" ");
  }
  if (ctx.project.templateType === "kids_animation") {
    return [
      "Feature-film family animation coverage inside ONE continuous story movie: follow the camera note in the SHOT block exactly.",
      "Vary shot size for emotion (wide for scale/establishing, medium for teamwork/action, close for fear/relief) — but stay on the SAME geography/world as the previous beat.",
      "At most one slow smooth move (push-in, soft arc, or gentle parallax past a foreground prop from this scene). Broadcast-safe: no shake, no whip pan.",
      "Single continuous take inside the clip; keep the speaking character readable with headroom and show set depth behind them.",
    ].join(" ");
  }
  return (
    ctx.character?.baseCameraPrompt ||
    "Fixed tripod camera. Medium close-up. No cuts, no zoom, no camera movement, no angle change."
  );
}

/**
 * Sinema anlatici oyunculugu. Klipler durgun gelmesin: sahnenin duygusu
 * (emotionLabel) bedende gorunur, her saniye fiziksel hareket vardir.
 * Yetiskin dram gerilimi (arzu, tahrik, kiskanclik, ofke) istenir; ancak
 * kiyafet uzerinde ve mahrem/cinsel eylem olmadan — aksi halde Veo reddeder.
 */
function cutawayPerformanceBlock(ctx: PromptContext): string {
  const seconds = Math.max(4, Math.min(20, ctx.project.clipSeconds || 8));
  const emotion = ctx.clip.emotionLabel?.replace(/\s+/g, " ").trim();
  const tone = ctx.clip.voiceTone?.replace(/\s+/g, " ").trim();
  const prevEmotion = ctx.previousClip?.emotionLabel?.replace(/\s+/g, " ").trim();
  return [
    "This is ACTED DRAMA, not b-roll: the people on screen perform the story beat with real feeling, like a scene from a feature film.",
    emotion
      ? `EMOTION FOR THIS TAKE (NON-NEGOTIABLE — must be unmistakable on camera): ${emotion}.`
      : "EMOTION FOR THIS TAKE: read the narration line and play its real emotion (desire, tension, jealousy, guilt, shame, fear, anger, heartbreak) — a neutral, blank or purely decorative shot is FORBIDDEN.",
    tone ? `Emotional temperature of the moment: ${tone}.` : "",
    prevEmotion ? `Emotional hangover from the previous take: ${prevEmotion} — continue from there, do not reset to neutral.` : "",
    "SHOW THE EMOTION IN THE BODY: eyes and gaze, breath rate, swallow, jaw, brow, flushed or blotchy skin, parted lips, trembling or clenched hands, shoulders, weight shifts, stepping closer or backing away, gripping fabric / a door / a glass / a phone.",
    "When the beat is rage they SHOUT or slam a door/table (no graphic injury). When it is heartbreak they may rage-cry — ugly wet face, not pretty sadness. Pretty frozen melancholy is forbidden.",
    "When two people share the frame, play the charge BETWEEN them: proximity, held or broken eye contact, a hand that hovers, a lean-in, a step back, a turn away.",
    `EMOTIONAL ARC INSIDE THE ${seconds}s: the feeling at second 0 must not be identical to the last second — it escalates, cracks, explodes or is swallowed. Something changes on the face.`,
    "MOVEMENT EVERY SECOND — a frozen tableau is FORBIDDEN: real blocking (steps, turns, reaching, sitting down, standing up, collapsing into a chair), an object actually handled, plus living world motion (rain, wind in curtains, traffic, steam, flickering practicals).",
    "One motivated camera move at most (slow push-in, gentle drift or handheld breath) — the picture must feel alive, never a still photograph, never a commercial plate.",
    "BROADCAST SAFE (so this renders): everyone stays fully clothed; no nudity, no sexual act, no intimate touching, no graphic blood. Crying, shouting, slamming a door, collapsing into a chair ARE ALLOWED when the emotion calls for it.",
    "Nobody on screen talks or lip-syncs: the narration is off-screen voice-over.",
    isNarratorHardConflictGenre(ctx.project.genre)
      ? "HARD CONFLICT PICTURE: this is not a melancholic insert. Bodies argue — slammed objects, jabbing hands, stepped-in space, shouted faces even while lips stay still for VO. Soft sad postcard blocking is FORBIDDEN."
      : "",
  ]
    .filter(Boolean)
    .join(" ");
}

function narratorOnCameraPerformanceBlock(ctx: PromptContext): string {
  const seconds = Math.max(4, Math.min(20, ctx.project.clipSeconds || 8));
  const emotion = ctx.clip.emotionLabel?.replace(/\s+/g, " ").trim();
  const tone = ctx.clip.voiceTone?.replace(/\s+/g, " ").trim();
  const prevEmotion = ctx.previousClip?.emotionLabel?.replace(/\s+/g, " ").trim();
  return [
    "FEATURE-FILM CONFESSION: this woman is ON CAMERA and SPEAKS the quoted line to camera in a lived-in room — not a voice-over plate, not a beauty commercial, not a seated catalog pose.",
    emotion
      ? `EMOTION FOR THIS TAKE (NON-NEGOTIABLE — unmistakable): ${emotion}.`
      : "EMOTION FOR THIS TAKE: play the real feeling of the line (heartbreak, rage, shame, fear, numbness that cracks) — pretty-neutral posing is FORBIDDEN.",
    tone ? `Voice/body temperature: ${tone}.` : "",
    prevEmotion ? `Emotional hangover from the previous take: ${prevEmotion} — continue, do not reset to calm host energy.` : "",
    "She may CRY as RAGE (wet cheeks, shaking breath, running mascara), RAISE HER VOICE or shout the quoted line, swear those words if they are in the quote, slam a table, stand up and sit back down, jab a finger at camera. Frozen sofa posing and pretty melancholy are forbidden.",
    `EMOTIONAL ARC INSIDE THE ${seconds}s: second 0 is not identical to the last second — the confession cracks, swells or is swallowed.`,
    clipSpeechPaceLock(seconds),
    "BROADCAST SAFE: fully clothed; no nudity, no graphic violence. Tears and a raised voice are allowed.",
  ]
    .filter(Boolean)
    .join(" ");
}

function performanceBlock(ctx: PromptContext): string {
  if (isCutaway(ctx)) return cutawayPerformanceBlock(ctx);
  if (ctx.project.templateType === "narrator") return narratorOnCameraPerformanceBlock(ctx);
  if (isKidsSong(ctx.project.templateType)) {
    const seconds = Math.max(4, Math.min(20, ctx.project.clipSeconds || 8));
    const emotion = ctx.clip.emotionLabel?.replace(/\s+/g, " ").trim();
    const tone = ctx.clip.voiceTone?.replace(/\s+/g, " ").trim();
    return [
      "Real YouTube-family music-video performance — NEVER a frozen pose or talking-head still.",
      `SECOND-BY-SECOND acting across the full ${seconds}s: every second a readable change (viseme, bounce, prop tap, brow, ear/tail).`,
      emotion ? `Face/body emotion this take (same locked singer): ${emotion}.` : "",
      tone ? `Physical energy (visual only): ${tone}.` : "",
      "Body stays ALIVE on the beat: knee bounce, shoulder groove, weight shifts left-right, head nod timed to the groove — energetic but broadcast-safe.",
      "LOCOMOTION LOCK: feet PLANT with real weight on every bounce/step — absolutely NO sliding, skating, gliding, rubbery foot-smear or ice-skate travel.",
      "Viseme timing matches every syllable of the quoted lyric; eyebrows, ears and tail react; eyes catch warm highlights; breath before phrases; smile grows with chorus energy.",
      "Choreography is playful and prop-interactive ON THE BEAT: clap, bounce-step, point TO a visible object, tap toys — always clearly readable; lyric props have real contact.",
      "Secondary animation EVERYWHERE and rhythm-locked: fur/fabric bounce, props reacting to kick/clap, background lights/particles/parallax, distant extras bouncing tiny.",
      "ANTI-GLITCH: face/body stay on-model every frame — no morph, melt, warp, flicker redesign or duplicate limbs. Same height and costume as IDENTITY LOCK.",
      "No frantic flailing, no dizzying spins, no risky stunts — peak musical staging, not chaos.",
    ]
      .filter(Boolean)
      .join(" ");
  }
  if (ctx.project.templateType === "kids_animation") {
    const emotion = ctx.clip.voiceTone ? ` Emotional tone for this beat (FOLLOW EXACTLY): ${ctx.clip.voiceTone}.` : "";
    const emotionLabel = ctx.clip.emotionLabel?.trim();
    const labelBit = emotionLabel ? ` Scene emotion label: ${emotionLabel}.` : "";
    const dialogue = ctx.clip.dialogue?.replace(/\s+/g, " ").trim() || "";
    const speakingIntro =
      dialogue.length > 0 &&
      /merhaba|selam|bugün|bugun|yapacağ|yapacag|arkadaş|arkadas|tanıt|tanit|hello|today|we will|we're going/i.test(
        dialogue
      );
    const speakingParts =
      dialogue.length > 0
        ? [
            `SPEAKING PERFORMANCE LOCK: deliver the dialogue with full syllable-sync and body life — never a frozen portrait while audio talks.`,
            speakingIntro
              ? "This is an INTRO/ADDRESS beat: face camera and/or friends; wave or open arms; point to a landmark or signature prop from THIS scene while explaining the plan; host energy."
              : "Gestures must match the spoken line; do not hold a statue pose or mime unrelated/contradicting actions that ignore the words.",
            "Every second: viseme timing for syllables, blinks, breath, weight shift, and at least one readable hand/arm gesture.",
            clipSpeechPaceLock(ctx.project.clipSeconds || 8),
          ]
        : [];
    return [
      "Acted theatrical 3D short-film performance — never a frozen portrait, never identical idle across clips.",
      ...speakingParts,
      speakingIntro
        ? "Scene props are secondary this beat: keep them visible in frame for continuity, but the PRIMARY action is animated talking + gesture."
        : "ANATOMY & WEIGHT: believable body mechanics for THIS scene's actual physical action (whatever the scene really describes) — real weight transfer, correct muscle engagement, correct contact points and balance. NO sliding/skating locomotion.",
      speakingIntro
        ? "HANDS: free for greeting/pointing gestures; may briefly touch a scene prop for storytelling without freezing."
        : "HANDS & PROPS: fingers grip THIS scene's actual props/objects with correct, physically believable contact and weight — never floating or mimed objects.",
      "FACE ACTING: big expressive eyes, clear brow/ear/tail acting, natural blinks, breath before speaking; cheeks flush with effort when the scene calls for it.",
      "Body language matches THIS scene's emotion and action ONLY.",
      "LOCOMOTION REALISM MAX: planted feet/body, solid grounded movement for this scene's real terrain; never slide, skate or float unrealistically.",
      "EMOTIONS ARE REAL AND OBVIOUS ON CAMERA, not a permanent smile:",
      "— Tense/fear/adrenaline: gasp, widened eyes, tight grip on whatever is at hand, quick breathing, body bracing, short freeze then committed move.",
      "— Relief: visible exhale, shoulders drop, grateful look to the friend who helped.",
      "— Exhausted: heavy steps, slower blinks, tired posture while still determined.",
      "— Triumph: authentic joy — not a flat grin.",
      "— Friendly intro/host: bright eyes, inviting smile WITH moving mouth, energetic shoulders — never a locked grin with silent lips.",
      "Broadcast-safe tension: short, resolved by teamwork (and equipment when relevant to this story), then visible relief — but WHILE it lasts it must FEEL real.",
      "If a second-by-second timeline is present, hit each second with a visible change in pose, prop contact OR expression.",
      "Every named supporting friend keeps locked face/colors/costume while they act — no mid-clip redesign (restate identity even with reference art).",
      `${emotion}${labelBit} No frantic flailing; intensity from clear acting and craft, not chaos.`,
    ].join(" ");
  }
  return "She remains seated and looks naturally toward the camera. Natural blinking, subtle facial expressions, minimal head movement and restrained hand gestures. Do not make her stand up or change position.";
}

function voiceBlock(ctx: PromptContext): string {
  if (isCutaway(ctx)) {
    const parts = [
      "The narrator voice-over keeps the exact same voice identity, accent and pitch across every clip of this film.",
      isNarratorHardConflictGenre(ctx.project.genre)
        ? "Delivery is HARD lived-in drama, not a sad commercial VO: shouted phrases, bitter spit, a crack that turns into a yell — melancholic whisper is FORBIDDEN unless the line is clearly numb. If the quote has Turkish swearing, speak those words loud and clear — do not skip or soften them."
        : "Delivery is lived-in drama, not a calm commercial VO: broken voice, tears in the throat, a raised shout that cracks — when the line demands it.",
    ];
    if (ctx.character?.baseVoicePrompt) parts.push(`Voice identity: ${ctx.character.baseVoicePrompt}.`);
    if (ctx.clip.voiceTone) parts.push(`Emotional delivery for this clip: ${ctx.clip.voiceTone}.`);
    return parts.join(" ");
  }
  if (ctx.project.templateType === "narrator") {
    const parts = [
      "Same woman, same voice identity as every other narrator take of this film.",
      isNarratorHardConflictGenre(ctx.project.genre)
        ? "She speaks ON CAMERA: angry, shouting, bitter or numb that SNAPS — never a polished presenter, never a melancholic poetry reading. Swear words in the quote are shouted with matching visemes. Soft sad confession energy is FORBIDDEN."
        : "She speaks ON CAMERA: cracked, tearful, angry or numb — never a polished presenter.",
    ];
    if (ctx.character?.baseVoicePrompt) parts.push(`Voice identity: ${ctx.character.baseVoicePrompt}.`);
    if (ctx.clip.voiceTone) parts.push(`Emotional delivery for this clip: ${ctx.clip.voiceTone}.`);
    return parts.join(" ");
  }
  if (isKidsSong(ctx.project.templateType)) {
    const parts = [
      SONG_VOICE_IDENTITY_LOCK,
      "SILENT VIDEO — uploaded master MP3 is the ONLY soundtrack (muxed onto this clip after download).",
      "Performer lip-syncs / mimes the quoted lyric with accurate visemes — NO generated singing or speech from the model.",
      ctx.isFirstClip
        ? "Establish consistent performer energy and mouth-sync style for the whole song."
        : "Continue the same performer identity and lip-sync quality as previous clips — same mouth shapes, same face, same singer.",
    ];
    if (ctx.clip.voiceTone?.trim()) {
      parts.push(`Physical performance energy for this line: ${ctx.clip.voiceTone.trim()} — visual only.`);
    }
    return parts.join(" ");
  }
  if (ctx.project.templateType === "kids_animation") {
    const parts: string[] = [
      ctx.isFirstClip
        ? "Single consistent character voice — warm, clear, broadcast-safe — but PERFORMANCE is HIGH-ENERGY adventure dubbing, not flat narration."
        : "Same voice identity as previous clip; continue the same adventure/story energy with fresh delivery for THIS beat.",
      "DELIVERY MUST MATCH THE BEAT: vary pace, volume and stress — never monotone, never three identical calm sentences.",
      "Adrenaline / crisis: short breathy bursts, urgent stress on the scene's key action words, audible effort.",
      "Relief: warmer exhale, slightly longer phrases, still alert.",
      "Fatigue: heavier, slower words; triumph: rising joy without cartoon scream.",
      "Clear sing-along diction; no whisper mud; no thin cartoon squeak.",
    ];
    if (ctx.character?.baseVoicePrompt) parts.push(`Voice: ${ctx.character.baseVoicePrompt}.`);
    if (ctx.clip.voiceTone) {
      parts.push(`Director delivery note (FOLLOW EXACTLY — tempo, emotion, stress): ${ctx.clip.voiceTone}.`);
    }
    return parts.join(" ");
  }
  const parts: string[] = [
    ctx.isFirstClip
      ? "Keep a single consistent voice identity, accent, pitch, pace and emotional tone throughout the clip."
      : "Keep the same voice identity, accent, pitch, pace and emotional tone as the previous clip.",
  ];
  if (ctx.character?.baseVoicePrompt) parts.push(`Voice: ${ctx.character.baseVoicePrompt}.`);
  if (ctx.clip.voiceTone) parts.push(`Emotional delivery for this clip: ${ctx.clip.voiceTone}.`);
  return parts.join(" ");
}

function musicBlock(ctx: PromptContext): string {
  if (!isKidsSong(ctx.project.templateType)) return "";
  return "NO AUDIO GENERATION: silent picture only. The uploaded MP3 (this song's exact take) is muxed onto the clip after download — forbid any singing, speech, humming or instrumental bed in this Flow export.";
}

function sceneNotesBlock(ctx: PromptContext): string {
  // Cocuk sablonlarinda Ingilizce yonetmen plani (imagePrompt) Flow'a girmeli;
  // Turkce panel ozeti tek basina yetersiz ve klipleri birbirine benzetir.
  if (isKidsContent(ctx.project.templateType)) {
    const english = ctx.clip.imagePrompt?.trim() || "";
    const seconds = Math.max(4, Math.min(20, ctx.project.clipSeconds || 8));
    const parts: string[] = [];
    parts.push(`Directed continuous ${seconds}-second theatrical 3D take — direct sequel to the previous beat of the same film.`);
    if (english) parts.push(`Scene: ${english}`);
    else if (ctx.clip.sceneDescription?.trim()) parts.push(`Scene: ${ctx.clip.sceneDescription.trim()}`);

    const hasTimeline = /(?:^|\n|\s)(?:second-by-second|\d+\s*[-–]\s*\d+\s*s\s*:)/i.test(english);
    if (!hasTimeline && isKidsContent(ctx.project.templateType)) {
      parts.push(
        isKidsSong(ctx.project.templateType)
          ? `Second-by-second MV staging required: invent a clear beat for each second 0-${seconds}s (groove bounce → lyric prop hit → reaction → soft handoff pose into the NEXT clip). No frozen idle longer than 1s. Planted feet — no sliding.`
          : `Second-by-second staging required: invent a clear beat for each second 0-${seconds}s (setup → physical action within THIS scene's own setting → reaction → soft cliffhanger into the NEXT clip). Name every on-screen cast member in the seconds they appear. No frozen idle longer than 1s.`
      );
    } else if (hasTimeline) {
      parts.push(
        `Follow the Second-by-second action timeline in chronological order across the full ${seconds}s — do not skip, reorder or hold a static pose across multiple seconds.`
      );
    }

    if (isKidsSong(ctx.project.templateType)) {
      const hero = ctx.character?.name?.trim();
      if (hero) {
        parts.push(
          `Lead singer this take (LOCKED identity — same face/colors/costume/HEIGHT/proportions every frame): ${hero}. Do not replace with a redesigned lookalike. Character fidelity outranks background detail.`
        );
      }
      if (ctx.clip.emotionLabel?.trim() || ctx.clip.voiceTone?.trim()) {
        parts.push(
          `Performance energy (face/body — same singer): ${[ctx.clip.emotionLabel, ctx.clip.voiceTone].filter(Boolean).join(" / ")}.`
        );
      }
      const lyrics = ctx.clip.dialogue?.replace(/\s+/g, " ").trim();
      if (lyrics) {
        parts.push(
          `Lyric-driven MV staging: singer mimes the FULL heard line ("${lyrics}") with syllable-sync + beat bounce every second.`
        );
        const map = formatWordByWordVisualMap(lyrics);
        if (map) parts.push(map);
      }
      parts.push(
        "Production density: fill foreground/mid/background with tangible set dressing and material detail — never a sparse empty plate."
      );
      parts.push(
        "LYRIC DRIVES PICTURE (COMPREHENSIVE): every content word of this clip's audio becomes a visible prop/action in the SAME moment; no generic dance that ignores a noun or verb; do not postpone a named thing to the next clip."
      );
      if (!ctx.isFirstClip) {
        parts.push(
          "Open as a MATCH-ON-ACTION continuation from the previous clip's last second — same MV set, same singer mid-groove, then advance the next lyric beat."
        );
      }
    }

    if (ctx.project.templateType === "kids_animation") {
      const castNames = (ctx.supportingCast ?? []).map((m) => m.name?.trim()).filter(Boolean) as string[];
      const hero = ctx.character?.name?.trim();
      const named = [...new Set([hero, ...castNames].filter(Boolean))];
      if (named.length) {
        parts.push(
          `On-screen cast this take (LOCKED identities — same face/colors/costume every frame): ${named.join(", ")}. Do not replace them with redesigned lookalikes.`
        );
      }
      if (ctx.clip.emotionLabel?.trim() || ctx.clip.voiceTone?.trim()) {
        parts.push(
          `Emotion lock (must be obvious on face/breath/posture for the whole take): ${[ctx.clip.emotionLabel, ctx.clip.voiceTone].filter(Boolean).join(" / ")}. Never default to a permanent smile.`
        );
      }
      const dial = ctx.clip.dialogue?.replace(/\s+/g, " ").trim();
      if (dial) {
        parts.push(
          `Dialogue-driven staging (MAXIMUM QUALITY): hero actively speaks the FULL line ("${dial}") — syllable-sync + gesture every second; every content word must land as visible action/prop/place/emotion in the same moment; never freeze while the line plays. ${clipSpeechPaceLock(seconds)}`
        );
      }
      const introBeat = !!dial && /merhaba|selam|bugün|bugun|yapacağ|arkadaş|hello|today/i.test(dial);
      parts.push(
        introBeat
          ? "Action clarity: intro/address beat — waving, pointing to a landmark or signature prop, inviting energy must be obvious; props may be visible for continuity but hands-on contact is optional this beat."
          : "Action clarity: every beat must be visually unambiguous — what is happening, who feels what, and which prop/object (if any) is used must be obvious without guessing. Show real, physically correct contact with that prop."
      );
      if (ctx.clip.sceneDescription?.trim()) {
        parts.push(
          `Scene-beat fidelity: honor every concrete detail in the panel summary — "${ctx.clip.sceneDescription.replace(/\s+/g, " ").trim().slice(0, 200)}" — staged with feature-film materials and contact.`
        );
      }
      if (!ctx.isFirstClip) {
        parts.push(
          "Open as a MATCH-ON-ACTION continuation from the previous clip's last second — same place in this story's setting, same props in hands, then advance."
        );
      }
    }
    return parts.join(" ");
  }
  if (isCutaway(ctx)) {
    const scene = ctx.clip.sceneDescription?.trim() || "";
    const visual = stripEmbeddedOnscreenTextTails(ctx.clip.imagePrompt?.trim() || "");
    const shot = extractTaggedBlock(visual, "SHOT");
    const timeline = visual.match(/\[TIMELINE[^\]]*\]\s*([^[]+)/i)?.[1]?.replace(/\s+/g, " ").trim() || "";
    const motion = extractTaggedBlock(visual, "MOTION");
    const emotion = extractTaggedBlock(visual, "EMOTION BEAT");
    const env = extractTaggedBlock(visual, "ENVIRONMENT");
    const parts = [
      scene ? `Scene: ${scene}` : "",
      shot ? `Directed shot: ${shot}` : "",
      timeline ? `Seconds: ${timeline}` : "",
      motion ? `Motion: ${motion}` : "",
      emotion ? `Emotion: ${emotion}` : "",
      env ? `Environment: ${env}` : "",
    ].filter(Boolean);
    if (parts.length) return parts.join("\n");
    if (visual) return visual.slice(0, 700);
    return scene || "A lived-in real-world cinema shot that stages every concrete place, object, weather and person named in the narration.";
  }
  return ctx.clip.sceneDescription ? `Scene: ${ctx.clip.sceneDescription}` : "";
}

/**
 * Fiziksel dunya gercekciligi (cocuk animasyonu).
 *
 * Hicbir temaya ozel ekipman/mekan metni YOKTUR: sahne hangi ortami tarif
 * ediyorsa fizik ona gore istenir, tekrar eden esyalar ise projenin kendi
 * tema prop kilidinden (storyGearLock) gelir.
 */
function adventureRealismBlock(ctx: PromptContext): string {
  if (ctx.project.templateType !== "kids_animation") return "";
  const gear = ctx.storyGearLock?.trim();
  const medium = inferKidsLocationMedium(
    [ctx.clip.sceneDescription, ctx.clip.imagePrompt, ctx.clip.dialogue].filter(Boolean).join("\n")
  );
  return [
    "Treat this as a REAL physical world staged in theatrical 3D — broadcast-safe but physically honest, feature-film prop continuity, staged ONLY in THIS story's own established setting as described in the scene block. Never invent a different setting, activity or equipment than the story describes.",
    kidsMediumPhysicsLock(medium),
    KIDS_FIXED_FILM_CRAFT_LOCK,
    gear || "",
    "PROP CONSISTENCY: any recurring tool/prop introduced earlier in this story keeps IDENTICAL colors and materials in every clip it appears — never recolor or redesign it mid-film. Gear must match the story world (yacht/dive story ≠ river raft kit).",
    "MOVEMENT CRAFT: characters interact with real weight and correct physical contact for the scene's actual action AND medium — the traces that action would really leave (footprints, splashes, bent grass, ripples, dust) stay believable and persist appropriately.",
    "ENVIRONMENT PHYSICS: particles/atmosphere that fit the scene, realistic light behavior for its materials (refraction/reflection in water, dappled light through leaves, haze over distance), and natural depth cues for scale.",
    "Never mime a prop and never recolor it mid-film — if dialogue names an object, show the SAME consistent version established earlier.",
    "ANTI-TELEPORT: do not jump from ship deck to swimming on dry land (or any biome mismatch) inside one take or between adjacent takes without an explicit transition beat.",
  ]
    .filter(Boolean)
    .join(" ");
}

/** Cizgi film / sinema yonetmenligi detaylari. */
function cinematicCraftBlock(ctx: PromptContext): string {
  if (!isKidsContent(ctx.project.templateType)) return "";
  if (isKidsSong(ctx.project.templateType)) {
    const pack = trySongVariety(ctx);
    const craftLead = pack
      ? `Premium animated music-video CGI craft (${pack.artDialect.id} dialect, theatrical feature lighting, not flat TV):`
      : "Premium animated music-video CGI craft (theatrical feature lighting, not flat TV):";
    const cameraLine = pack
      ? `Camera this clip follows the PROJECT LOOK PACK in STYLE — same world, new lens/move only.`
      : "Camera grammar: medium for performance, occasional push-in on the hook; one slow push-in or soft beat-bob max; gentle parallax on a foreground prop.";
    return [
      craftLead,
      "Motivated key/fill/rim matched to THIS MV set; soft bounce color from nearby props; subtle volumetric sparkle only when it fits the song world.",
      "Composition: clear singer silhouette, readable eye-lines, foreground lyric-prop framing, mid-ground performance, deep DETAILED background — no empty voids.",
      cameraLine,
      "Animation polish: overlapping action on hair/fur/fabric, settle after landings, anticipation before claps/jumps, follow-through on prop hits, secondary motion every second.",
      "Material storytelling: weave, grain, glaze, wear and thickness on every prop — denser than a toy commercial void.",
      "ANTI-GLITCH craft: stable mesh, planted feet, no morph/warp/slide, no flicker redesign between frames.",
    ].join(" ");
  }
  return [
    "Theatrical family-CGI craft (Pixar/DreamWorks feature, not flat TV lighting):",
    "Motivated key/fill/rim matched to THIS scene's real setting (e.g. cool blue-green bounce for underwater/sea, warm dappled light for forest, cool practicals for space, warm golden hour for a village); subtle motivated flare only.",
    "Composition: clear silhouettes, readable eye-lines, foreground prop framing, mid-ground action, deep background for scale — no empty voids.",
    "Camera grammar: wide for scale, medium for teamwork/action, close for fear/relief; one slow push-in or soft arc max; gentle parallax on a foreground element from this scene.",
    "Animation polish: overlapping action on hair/fur/fabric/water, settle after landings, anticipation before key actions, follow-through on swings/strokes, cloth/prop secondary motion every second.",
    "Material storytelling: wear, moisture, dust or texture appropriate to this story's own world that STAYS consistent clip to clip (wear accumulates, colors do not change).",
    "Color story: cohesive palette tied to this story's established world and any locked prop colors; never random neon props.",
    "Micro inserts inside the continuous take: a hand making real contact with a signature prop, a believable material detail unique to this scene's setting.",
  ].join(" ");
}

/**
 * Sozlerde gecen nesne/sayi ile kadroyu kilitler.
 * Ornek: "kac vagon 1 2 3" -> ekranda sayilabilir vagonlar zorunlu.
 */
function lyricVisualLockBlock(ctx: PromptContext): string {
  if (ctx.project.templateType !== "kids_song") return "";
  const lyrics = ctx.clip.dialogue.replace(/\s+/g, " ").trim();
  const wordMap = formatWordByWordVisualMap(lyrics);
  const must = mustShowFromAudio(lyrics);
  return [
    SONG_LYRIC_PICTURE_SYNC_LOCK,
    "COMPREHENSIVE lyric-to-picture AND lyric-to-audio fidelity — every heard content word, not a summary.",
    `The audio for THIS clip (sung + any spoken/talk-sing) is exactly: "${lyrics}".`,
    wordMap,
    must ? `Must-show this take: ${must}` : "",
    "What is heard must be those exact words; what is seen must illustrate those SAME words in the SAME moment — not a generic dance.",
    "Every object, vehicle, animal, toy, food, place, color, verb or NUMBER named in those lyrics must be physically present in THIS frame with the correct count.",
    "Props have real materials (wood grain, paint chips, rubber wheels, fabric weave), thickness, contact shadows and ground contact — close-up readable detail, not plastic blobs.",
    "If the character counts 1-2-3, they point to or tap three DISTINCT visible items in order — never mime counting empty air.",
    "Do not replace named props with vague background decoration or unrelated toys. Do not postpone a named thing to the next clip.",
    "Read the CLEAR MUSIC-VIDEO DIRECTOR BRIEF in the SHOT block in order: heard line → word-by-word map → must-show props → shot plan.",
    "Stage like a premium animated music video: singer in mid-ground, lyric props in clear focus, and a DENSE living background with depth, textures and motion — not a static portrait on an empty void.",
  ]
    .filter(Boolean)
    .join(" ");
}

function songPictureConfirmBlock(ctx: PromptContext): string {
  if (ctx.project.templateType !== "kids_song") return "";
  const support = (ctx.supportingCast ?? []).map((m) => m.name?.trim()).filter(Boolean) as string[];
  return formatSongPictureConfirm({
    audioLine: ctx.clip.dialogue || "",
    singerName: ctx.character?.name,
    appearanceLock: ctx.character?.baseAppearancePrompt,
    wardrobeLock: ctx.character?.baseWardrobePrompt,
    supportingNames: support,
  }).replace(/^\[SONG PICTURE CONFIRM[^\]]*\]\s*/i, "");
}

/** Konusmali kids film: hikaye/diyalog kelimelerinin gorsel sadakati (sarki lyric lock karsiligi). */
function dialogueVisualLockBlock(ctx: PromptContext): string {
  if (ctx.project.templateType !== "kids_animation" && ctx.project.templateType !== "narrator") return "";
  const dial = ctx.clip.dialogue?.replace(/\s+/g, " ").trim() || "";
  const scene = [ctx.clip.sceneDescription, ctx.clip.imagePrompt].filter(Boolean).join(" ").trim();
  if (ctx.project.templateType === "narrator") {
    return [
      "STORY-WORD VISUAL LOCK (CINEMA — PICTURE ONLY):",
      "Stage the people, places, weather and objects named in SHOT / ENVIRONMENT / SET DRESSING.",
      "Do NOT paint spoken words onto the picture, props, phones, glass, fogged windows or clothing. Speech is AUDIO only.",
      dial ? `The spoken line is AUDIO (never a subtitle): "${dial}".` : "",
      "Show meaning through acting, props and weather — not letters.",
    ]
      .filter(Boolean)
      .join(" ");
  }
  if (!dial && !scene) {
    return "STORY-WORD VISUAL LOCK pending dialogue — once lines exist, every content word must be staged as tangible cinema detail.";
  }
  return buildStoryWordVisualLock(dial, scene, ctx.project.clipSeconds || 8);
}

function negativeBlock(ctx: PromptContext): string {
  const parts: string[] = [];
  parts.push(
    "Negative constraints: no subtitles, no captions, no karaoke text, no on-screen writing, no clothing labels, no chalkboard letters, no logos, no watermarks, no burned-in dialogue text."
  );
  if (ctx.project.templateType === "narrator") {
    parts.push(
      "Also forbid: glossy beauty-ad lighting, catalog posing, perfume-commercial sheen, plastic skin, empty hotel interiors, frozen pretty sadness, sitting-still product-ad talking-head."
    );
  }
  if (isKidsSong(ctx.project.templateType)) {
    parts.push(
      "Also forbid: empty flat void backgrounds, sparse undetailed sets, missing sky/horizon/ground, sliding/skating feet, face or body morphing, melting limbs, warped proportions, flicker redesigns, mirrored twin duplicates, teleporting props, silent music bed, changing the lead singer voice between clips, character redesign/recolor/identity change between clips, costume drift, height/proportion changes, extra limbs, frozen idle longer than 1s."
    );
  }
  const negative = ctx.character?.negativePrompt?.trim();
  if (negative) parts.push(`Additional restrictions: ${negative}`);
  return parts.join(" ");
}

function flowCharacterBlock(ctx: PromptContext): string {
  // Kesitte @ ana kadin yok. Kameradaki itirafta ana kadin @ ile gelir.
  if (ctx.project.templateType === "narrator") {
    if (!ctx.project.useFlowCharacter) return "";
    const refs: string[] = [];
    const norm = (r: string) => r.replace(/^@+/, "").trim().toLowerCase();
    const pushRef = (raw: string | null | undefined) => {
      const t = raw?.trim();
      if (!t) return;
      const withAt = t.startsWith("@") ? t : `@${t}`;
      if (refs.some((r) => norm(r) === norm(withAt))) return;
      refs.push(withAt);
    };
    if (!isCutaway(ctx)) {
      pushRef(ctx.character?.flowCharacterReference);
    } else {
      pushRef(ctx.sceneCharacter?.flowCharacterReference);
      for (const member of ctx.supportingCast ?? []) {
        if (member.role === "main") continue;
        pushRef(member.flowCharacterReference);
      }
    }
    if (refs.length === 0) return "";
    return `${refs.join("\n")}\n\n`;
  }
  // Flow @karakter etiketleri YALNIZCA proje ayari aciksa — kapaliyken yan
  // karakter @Ada/@Ruzgar satirlari ana kahramani ezip videoda yok edebiliyordu.
  if (!ctx.project.useFlowCharacter) return "";

  const refs: string[] = [];
  const norm = (r: string) => r.replace(/^@+/, "").trim().toLowerCase();
  const pushRef = (raw: string | null | undefined) => {
    const t = raw?.trim();
    if (!t) return;
    const withAt = t.startsWith("@") ? t : `@${t}`;
    if (refs.some((r) => norm(r) === norm(withAt))) return;
    refs.push(withAt);
  };

  // Sarki: bu klibin soyleyeni once, sonra tum kadro @ad'leri.
  // Diger sablonlar: ana kahraman ilk @ — Flow once onu baglasin.
  if (isKidsSong(ctx.project.templateType)) {
    pushRef(ctx.sceneCharacter?.flowCharacterReference);
  }
  pushRef(ctx.character?.flowCharacterReference);

  for (const member of ctx.supportingCast ?? []) {
    if (member.role === "main") continue;
    if (ctx.character?.name && member.name?.trim().toLowerCase() === ctx.character.name.trim().toLowerCase()) continue;
    pushRef(member.flowCharacterReference);
  }
  if (refs.length === 0) return "";
  return `${refs.join("\n")}\n\n`;
}

/**
 * SARKI KLIBI PROMPTU — SIFIRDAN, TEMIZ MIMARI.
 *
 * Ilkeler (Veo/Flow'da ekrana yazi basilmasini onlemek + soz-gorsel esitligi):
 * 1) KISA: nihai prompt ~4-6k karakter — asla kesilmez, hicbir kural dusmez.
 * 2) Soz metni TUM promptta YALNIZCA composeShotPrompt icinde 1 kez tirnaklanir;
 *    tirnakli metin yigini Veo'ya "bunu ekrana yaz" sinyali verir.
 * 3) Yazi yasagi tek kompakt blok (bas) + tek kisa final kilidi (son) — kayit
 *    sirasinda stampNoOnscreenTextLock ekler; burada tekrarlanmaz.
 * 4) Dunya kilidi + saniye-saniye plan composeShotPrompt cekirdeginde.
 */
function composeKidsSongFlowPrompt(ctx: PromptContext): string {
  const lead = ctx.sceneCharacter ?? ctx.character;
  const seconds = Math.max(4, Math.min(20, ctx.project.clipSeconds || 8));
  const refs = flowCharacterBlock(ctx);

  const header = `[ANIMATED SONG FILM — CLIP ${ctx.clip.index} — ONE CONTINUOUS ${seconds}s SHOT]`;
  // Onceki klibin SOMUT bitisi (son saniyeler, sahne, duygu) prompta girer;
  // genel "match-on-action" cumlesi tek basina kopmayi engellemiyordu.
  const continuity = formatSongClipBridge({
    clipIndex: ctx.clip.index,
    isFirstClip: ctx.isFirstClip,
    previousImagePrompt: ctx.previousClip?.imagePrompt,
    previousScene: ctx.previousClip?.sceneDescription,
    previousEmotion: ctx.previousClip?.emotionLabel,
    previousVoiceTone: ctx.previousClip?.voiceTone,
  });

  const castLines: string[] = [];
  if (lead?.name?.trim()) {
    const app = (lead.baseAppearancePrompt || "").replace(/\s+/g, " ").trim().slice(0, 420);
    const ward = ((lead as { baseWardrobePrompt?: string | null }).baseWardrobePrompt || "")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 220);
    castLines.push(
      `Lead performer: ${lead.name.trim()}${app ? ` — ${app}` : ""}${ward ? `. Costume: ${ward}` : ""}.`
    );
  }
  const friends = (ctx.supportingCast ?? [])
    .filter((m) => m.name?.trim())
    .map((m) => {
      const app = (m.baseAppearancePrompt || "").replace(/\s+/g, " ").trim().slice(0, 100);
      return app ? `${m.name.trim()} (${app})` : m.name.trim();
    });
  if (friends.length > 0) {
    castLines.push(`Friends of this song (same design in every clip): ${friends.join("; ")}.`);
  }
  castLines.push(
    "Every character stays 100% on-model with their reference image in every frame — same face, species, proportions, colors and costume. Only this cast appears; no new or off-model characters."
  );

  const pack = trySongVariety(ctx);
  const custom = ctx.project.visualStyle?.trim();
  const preset = VISUAL_STYLE_PRESETS.find((p) => p.id === (custom || "pixar3d"));
  const family = visualStyleFamilyOf(ctx.project.templateType, custom);
  const isAnime = family === "anime2d";
  const isLive = family === "live-action";
  // Stil blogu TEK kaynaktir: sanat dili + look pack kilidi + aile kilidi.
  // Hicbir parca burada veya SHOT PLAN icinde ikinci kez yazilmaz — tekrar,
  // 8k limitinde gercek yonergenin kesilmesine yol aciyordu.
  // Hazir on ayarlar (gercekci / sinematik / belgesel) fizik gercekligini
  // zaten ayrintili anlatir; uzerine LIVE_ACTION_SONG_REALISM eklemek ayni
  // kurallari ikinci kez yazip promptu limitin uzerine cikariyordu.
  const livePreset = isLive ? preset?.prompt : "";
  const styleBase = isLive
    ? livePreset || custom || VISUAL_STYLE_PRESETS.find((p) => p.id === "photorealistic")!.prompt
    : pack && !isAnime
      ? pack.artDialect.prompt
      : (preset ?? VISUAL_STYLE_PRESETS.find((p) => p.id === "pixar3d")!).prompt;
  const liveWorld = isLive
    ? detectSongWorld(
        [ctx.clip.dialogue || "", ctx.project.topic || "", ctx.project.title || "", ctx.clip.sceneDescription || ""].join(
          "\n"
        )
      )
    : null;
  const style = [
    styleBase,
    isLive && pack
      ? formatStyleOverlayNeutral(pack, ctx.clip.index)
      : pack && !isAnime
        ? formatLookPackLock(pack, ctx.clip.index)
        : "",
    ctx.project.aspectRatio === "9:16" ? "Vertical 9:16 composition." : "Cinematic 16:9 composition.",
    isLive
      ? livePreset
        ? // Preset zaten fizik anlatir; yalnizca kisa mekan vurgusu (8k).
          "Lyric places fill the frame as dense REAL filmed geography; costumed mascots perform ON that real ground with contact shadows — never a flat cartoon plate."
        : LIVE_ACTION_SONG_REALISM
      : "Render quality: physically based materials, groomed fur strands, living eyes with catchlights, soft global illumination, contact shadows under every character and prop, believable weight in every move.",
    worldFamilyLock(family),
  ]
    .filter(Boolean)
    .join(" ");

  const audio =
    "Video-only clip: external pre-recorded song is the ONLY soundtrack. No voice-over. NO on-screen text — no üst yazı, no alt yazı/subtitles, no captions, no lyric overlays anywhere in frame.";

  const lipSync = songLipSyncLock({
    seconds,
    isFirstClip: ctx.isFirstClip,
    singerName: lead?.name,
    hasLyrics: Boolean(ctx.clip.dialogue?.trim()),
  });

  // Sahne planlari 3D lehcede yazilir; canli cekim projede son metin de
  // canli-cekim diline cevrilir ki [STYLE] kilidiyle celismesin.
  // Sozlerdeki mekanlar fotografik yogunlukta guclendirilir (SET + PLACE LOCK).
  const rawShot = isLive
    ? boostLiveActionShotPlan(
        convertShotPlanToLiveAction(ctx.clip.imagePrompt.trim()),
        ctx.clip.dialogue || "",
        [ctx.project.topic || "", ctx.project.title || "", liveWorld?.key || ""].join(" ")
      )
    : ctx.clip.imagePrompt.trim();

  // 8000 hard limit: sabit bloklar once yer kaplar; shot plan kalan butceye
  // kirpilir (SET/soz basta oldugu icin kuyruk kesilse de kilitler kalir).
  const stampOverhead = 640;
  const fixedCore = [
    `${refs}${header}`,
    continuity,
    `[CAST — LOCKED EVERY FRAME]\n${castLines.join(" ")}`,
    `[STYLE]\n${style}`,
    `[LIP SYNC]\n${lipSync}`,
    `[AUDIO]\n${audio}`,
  ].join("\n\n");
  const shotBudget = Math.max(900, FLOW_PROMPT_MAX - stampOverhead - fixedCore.length - 40);
  const shotPlan = rawShot.length <= shotBudget ? rawShot : rawShot.slice(0, shotBudget).trim();

  return [
    `${refs}${header}`,
    continuity,
    `[CAST — LOCKED EVERY FRAME]\n${castLines.join(" ")}`,
    `[STYLE]\n${style}`,
    `[PERFORMANCE — SHOT PLAN]\n${shotPlan}`,
    `[LIP SYNC]\n${lipSync}`,
    `[AUDIO]\n${audio}`,
  ].join("\n\n");
}

/** Tek klip icin nihai Flow promptunu uretir. */
export function buildClipPrompt(ctx: PromptContext): string {
  if (ctx.project.templateType === "kids_song") return composeKidsSongFlowPrompt(ctx);

  const template =
    ctx.project.templateType === "narrator"
      ? isCutaway(ctx)
        ? DEFAULT_CUTAWAY_TEMPLATE
        : DEFAULT_NARRATOR_TEMPLATE
      : isCutaway(ctx)
        ? DEFAULT_CUTAWAY_TEMPLATE
        : ctx.project.promptTemplate?.trim() || defaultTemplateFor(ctx.project.templateType, ctx.clip.shotType);

  const forceKidsNoText = isKidsContent(ctx.project.templateType);
  const subtitleCtx: PromptContext = { ...ctx, project: { ...ctx.project, allowSubtitles: false } };

  const replacements: Record<string, string> = {
    STYLE: styleBlock(ctx),
    CHARACTER_REFERENCE: characterReferenceBlock(ctx),
    CHARACTER_FIDELITY: characterFidelityBlock(ctx),
    SCENE_CONTINUITY: sceneContinuityBlock(ctx),
    CAMERA: cameraBlock(ctx),
    PERFORMANCE: performanceBlock(ctx),
    VOICE: voiceBlock(ctx),
    LANGUAGE: ctx.project.speechLanguage,
    DIALOGUE: ctx.clip.dialogue.replace(/"/g, "'"),
    HARD_EMOTION: hardEmotionBlock(ctx),
    SUBTITLES: subtitlesBlock(subtitleCtx),
    SPEECH_FIDELITY: speechFidelityBlock(ctx),
    NEGATIVE: negativeBlock(subtitleCtx),
    FLOW_CHARACTER: flowCharacterBlock(ctx),
    SCENE_NOTES: sceneNotesBlock(ctx),
    MUSIC: musicBlock(ctx),
    LYRIC_VISUAL_LOCK: lyricVisualLockBlock(ctx),
    SONG_PICTURE_CONFIRM: songPictureConfirmBlock(ctx),
    DIALOGUE_VISUAL_LOCK: dialogueVisualLockBlock(ctx),
    ADVENTURE_REALISM: adventureRealismBlock(ctx),
    CINEMATIC_CRAFT: cinematicCraftBlock(ctx),
    WORLD_DETAIL: worldDetailBlock(ctx),
    SECOND_BY_SECOND: secondBySecondBlock(ctx),
  };

  let prompt = template;
  for (const [key, value] of Object.entries(replacements)) {
    prompt = prompt.split(`{{${key}}}`).join(value);
  }

  // Eski/ozel sablonlarda {{SPEECH_FIDELITY}} veya [ON-SCREEN TEXT] yoksa
  // kurallari yine de ekle — Veo altyazi/soz sapmasini engellemek icin.
  if (!template.includes("{{SPEECH_FIDELITY}}")) {
    prompt = `${prompt}\n\n[SPEECH / LYRIC LOCK]\n${speechFidelityBlock(ctx)}`;
  }
  if (!template.includes("{{SUBTITLES}}") && !template.includes("[ON-SCREEN TEXT]")) {
    prompt = `${prompt}\n\n[ON-SCREEN TEXT]\n${subtitlesBlock(subtitleCtx)}`;
  }
  if (
    (ctx.project.templateType === "kids_animation" || ctx.project.templateType === "narrator") &&
    !template.includes("{{DIALOGUE_VISUAL_LOCK}}") &&
    !/\[STORY WORD/i.test(prompt)
  ) {
    const lock = dialogueVisualLockBlock(ctx);
    if (lock) prompt = `${prompt}\n\n[STORY WORD → PICTURE LOCK]\n${lock}`;
  }

  if (ctx.project.templateType === "kids_song" && !/\[SONG PICTURE CONFIRM/i.test(prompt)) {
    const confirm = songPictureConfirmBlock(ctx);
    if (confirm) prompt = `[SONG PICTURE CONFIRM — AUDIO DRIVES FRAME]\n${confirm}\n\n${prompt}`;
  }

  // Altyazi kapaliyken prompt SONUNA ekstra sert kilit (tekrar / agirlik).
  // Acikken dil kilidi sona yapisir (yanlis dil altyazisini engellemek icin).
  // Cocuk animasyonu / sarki: her klipte (N=8 veya N=50) yazi yasagi zorunlu.
  const endLock = subtitlesEndLock(subtitleCtx);
  if (endLock) {
    prompt = `${prompt}\n\n${endLock}`;
  }

  // Dil kilidi en basa (Flow uzun promptlarda ortayi kesebiliyor / oncelik baslarda)
  const lang = ctx.project.speechLanguage?.trim() || "Turkish";
  const speechLangLock = [
    "[SPEECH LANGUAGE LOCK — NON-NEGOTIABLE]",
    `Spoken audio MUST be ${lang} only.`,
    `All audible dialogue MUST be ${lang}. Do not switch language. Especially do not switch to English unless ${lang} itself is English.`,
    `Deliver the quoted dialogue verbatim in ${lang} — never translate or paraphrase.`,
  ].join(" ");

  const textBanHead = [
    "[NO ON-SCREEN TEXT — NON-NEGOTIABLE]",
    "Zero subtitles/captions/karaoke/titles/labels in ANY language (including English auto-captions).",
    "FORBIDDEN: text on the TOP of the frame, text on the BOTTOM of the frame, YouTube caption bars, karaoke strips, lower-thirds.",
    "Same ban for 9:16 vertical and 16:9 horizontal. Clean picture only — override any default captioning.",
    forceKidsNoText
      ? "This ban applies to EVERY clip of this animated short equally — first scene through last scene."
      : "This ban applies to every clip of this film equally — first scene through last scene.",
  ].join(" ");

  const castLock = isKidsContent(ctx.project.templateType) ? `${FLOW_ANIMATED_CAST_LOCK}\n\n` : "";
  const headLocks = [castLock, speechLangLock, textBanHead].filter(Boolean).join("\n\n");
  if (!/\[SPEECH LANGUAGE LOCK/i.test(prompt)) {
    const atRefs = prompt.match(/^(?:@[^\n]+\n)+/);
    if (atRefs) {
      prompt = `${atRefs[0]}\n${headLocks}\n\n${prompt.slice(atRefs[0].length).replace(/^\n+/, "")}`;
    } else {
      prompt = `${headLocks}\n\n${prompt}`;
    }
  } else if (!/\[NO ON-SCREEN TEXT/i.test(prompt)) {
    prompt = prompt.replace(
      /(\[SPEECH LANGUAGE LOCK[^\]]*\][^\n]*(?:\n(?!\[)[^\n]*)*)/,
      `$1\n\n${textBanHead}`
    );
  }

  // Karakter kimlik kilidi: sarki kliplerinde HER ZAMAN en one (referans kapali olsa bile)
  if (ctx.project.templateType === "kids_song" && !/\[IDENTITY LOCK/i.test(prompt)) {
    const identityLock = [
      "[IDENTITY LOCK — MAXIMUM CHARACTER CONSISTENCY — EVERY CLIP]",
      SONG_CHARACTER_FIDELITY_LOCK,
      ctx.character?.baseAppearancePrompt?.trim()
        ? `Written FULL lock: ${ctx.character.baseAppearancePrompt.trim()}`
        : "",
      ctx.character?.baseWardrobePrompt?.trim()
        ? `Written costume lock: ${ctx.character.baseWardrobePrompt.trim()}`
        : "",
      ctx.project.useReference
        ? "Uploaded reference/turnaround reinforces this lock 1:1 — never redesign away from it."
        : "Keep the written lock identical even without a reference sheet.",
    ]
      .filter(Boolean)
      .join(" ");
    const atRefs = prompt.match(/^(?:@[^\n]+\n)+/);
    if (atRefs) {
      prompt = `${atRefs[0]}\n${identityLock}\n\n${prompt.slice(atRefs[0].length).replace(/^\n+/, "")}`;
    } else if (/\[SPEECH LANGUAGE LOCK/i.test(prompt)) {
      prompt = prompt.replace(/(\[SPEECH LANGUAGE LOCK[\s\S]*?\n\n)/, `$1${identityLock}\n\n`);
    } else {
      prompt = `${identityLock}\n\n${prompt}`;
    }
  } else if (ctx.project.useReference && !/\[IDENTITY LOCK/i.test(prompt)) {
    const onScreenNames = [
      ctx.sceneCharacter?.name?.trim(),
      ...(ctx.supportingCast ?? []).map((m) => m.name?.trim()),
    ].filter(Boolean) as string[];
    const identityLock =
      ctx.project.templateType === "narrator"
        ? isCutaway(ctx)
          ? onScreenNames.length
            ? [
                "[IDENTITY LOCK — ON-SCREEN CAST ONLY]",
                "Uploaded reference image(s) are FRONT+BACK turnaround sheets for the people in THIS shot only (one person per sheet: left=front, right=back).",
                `Lock these identities 1:1: ${onScreenNames.join(", ")}.`,
                "They are NOT different people and NOT the narrator. Match that exact face, hair, age and wardrobe in EVERY frame.",
                "Do not morph faces, invent extras, or reuse a different clip's person. If sheets are attached, ignore any memory of a previous last-frame face.",
              ].join(" ")
            : [
                "[IDENTITY LOCK — NO NAMED FACE]",
                "No character sheet is the star of this shot. Keep extras anonymous and unreadable.",
                "CUTAWAY: the narrator woman is NOT in this shot. Do not invent a recurring new face.",
              ].join(" ")
          : [
              "[IDENTITY LOCK — NARRATOR ON CAMERA]",
              "Uploaded reference image(s) are FRONT+BACK turnaround sheets for the storyteller woman (one person: left=front, right=back).",
              "This is the SAME woman in every narrator take. Match that exact face, hair, age and wardrobe.",
              "Lived-in drama look — not a model, not a commercial host. Do not morph her into a different person.",
            ].join(" ")
        : [
            "[IDENTITY LOCK — MAXIMUM CHARACTER CONSISTENCY]",
            "Uploaded reference image(s) are FRONT+BACK turnaround sheets (one character per sheet: left=front, right=back).",
            "They are NOT different people — match that exact face, silhouette, colors and costume 1:1 in EVERY frame.",
            "Do not redesign, recolor, change identity or morph anyone. Character consistency outranks camera tricks and background detail.",
            ctx.project.templateType === "kids_animation"
              ? "EVEN WITH references present: keep FULL written appearance + wardrobe locks for hero and cast in the prompt — references reinforce, they never replace verbal detail."
              : "",
          ]
            .filter(Boolean)
            .join(" ");
    const atRefs = prompt.match(/^(?:@[^\n]+\n)+/);
    if (atRefs) {
      prompt = `${atRefs[0]}\n${identityLock}\n\n${prompt.slice(atRefs[0].length).replace(/^\n+/, "")}`;
    } else if (/\[SPEECH LANGUAGE LOCK/i.test(prompt)) {
      prompt = prompt.replace(/(\[SPEECH LANGUAGE LOCK[\s\S]*?\n\n)/, `$1${identityLock}\n\n`);
    } else {
      prompt = `${identityLock}\n\n${prompt}`;
    }
  }

  // Bos bloklardan kalan fazla bos satirlari sadelestir
  prompt = prompt.replace(/\n{3,}/g, "\n\n").trim();
  if (isKidsContent(ctx.project.templateType)) {
    prompt = sanitizeKidsPromptForFlow(prompt);
  }
  return stampNoOnscreenTextLock(prompt);
}
