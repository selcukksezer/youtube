"""
Style Profile Manager.
Adapted and enhanced from naqashafzal/AI-Content-Studio (api_clients.py).
Centralizes content styles, multi-modal prompt tuning, TTS delivery cadence,
cinematography aesthetic matrices, and subtitle styling for YouTube Shorts.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union


class ContentStyle(str, Enum):
    PODCAST = "podcast"
    ASMR = "asmr"
    DOCUMENTARY = "documentary"
    STORY = "story"
    KIDS_STORY = "kids_story"
    HORROR = "horror"
    VIRAL_VIDEO = "viral_video"
    PRODUCT_AD = "product_ad"
    STOIC_FACTS = "stoic_facts"


@dataclass
class StyleProfile:
    name: str
    script_prompt: str
    tts_cadence_cue: str
    video_aesthetic: str
    image_prompt_suffix: str
    research_angle: str
    target_wpm: int
    subtitle_font: str
    primary_color_rgb: tuple
    outline_color_rgb: tuple


STYLE_PROFILES: Dict[ContentStyle, StyleProfile] = {
    ContentStyle.PODCAST: StyleProfile(
        name="Podcast",
        script_prompt=(
            "Craft an ultra-realistic, multi-layered dual-host conversation. "
            "Utilize advanced conversational dynamics: interruptions, active listening ('mm-hmm', 'bak burası önemli'), "
            "tangents, and callbacks. Balance deep analytical insights with relatable analogies."
        ),
        tts_cadence_cue="(Speaking with authentic conversational cadence, utilizing natural pauses, micro-breaths, and varied intonation)",
        video_aesthetic="Cinematic 4K podcast studio, volumetric soft-box lighting, shallow depth of field (f/1.8), warm amber and teal tone grading",
        image_prompt_suffix="cinematic photography of modern broadcast studio, ambient warm lighting, acoustic wall panels, bokeh background",
        research_angle="Uncover counter-narratives, controversial expert opinions, and hidden connections that challenge conventional wisdom",
        target_wpm=145,
        subtitle_font="Arial Black",
        primary_color_rgb=(255, 255, 255),
        outline_color_rgb=(20, 20, 20),
    ),
    ContentStyle.ASMR: StyleProfile(
        name="ASMR Video",
        script_prompt=(
            "Compose a deeply immersive, sensory-rich script. Prioritize auditory and tactile descriptions over action. "
            "Sentences must be profoundly rhythmic, slow, and hypnotic. Utilize repetition and phonetic softness."
        ),
        tts_cadence_cue="(Whispering with extreme intimacy and softness. Enunciate every syllable with deliberate, glacial pacing)",
        video_aesthetic="Hyper-macro 8K cinematography, 120fps slow-motion, exquisite focus on tactile textures, dreamlike pastel color grading",
        image_prompt_suffix="award-winning macro photography, razor-sharp texture focus, buttery smooth bokeh, tranquil earth tones",
        research_angle="Identify highly specific sensory details, textural anomalies, and rhythmic acoustic properties",
        target_wpm=105,
        subtitle_font="Trebuchet MS",
        primary_color_rgb=(220, 245, 255),
        outline_color_rgb=(40, 60, 80),
    ),
    ContentStyle.DOCUMENTARY: StyleProfile(
        name="Documentary",
        script_prompt=(
            "Adopt the gravitas of a BBC/HBO premium documentary. Structure with a cold open, historical contextualization, "
            "rising tension, and a profound philosophical conclusion. Interweave empirical facts with human emotional stakes."
        ),
        tts_cadence_cue="(Speaking with immense gravitas, profound resonance, and measured authority. Strategic silence to let heavy statements linger)",
        video_aesthetic="Award-winning IMAX documentary cinematography, anamorphic lens, slow deliberate push-ins (Ken Burns), dramatic chiaroscuro lighting",
        image_prompt_suffix="Pulitzer-prize winning photojournalism, high-contrast desaturated cinematic color, gritty realism, rule-of-thirds",
        research_angle="Source primary empirical records, verified historical data, direct quotes from historians, and socio-economic impacts",
        target_wpm=135,
        subtitle_font="Georgia",
        primary_color_rgb=(245, 240, 220),
        outline_color_rgb=(10, 10, 10),
    ),
    ContentStyle.STORY: StyleProfile(
        name="Story",
        script_prompt=(
            "Construct a masterful narrative utilizing the Hero's Journey framework. Establish deep character motivations, "
            "escalating stakes, and visceral emotional beats. Employ 'show, don't tell' environmental storytelling."
        ),
        tts_cadence_cue="(Speaking with dynamic theatrical range. Shift between hushed tension during buildup and explosive energy at the climax)",
        video_aesthetic="Hollywood blockbuster cinematography (ARRI Alexa 65), dramatic motivated lighting, dynamic camera blocking, lush stylized color grading",
        image_prompt_suffix="epic concept art, dramatic lighting, intense emotional resonance, hyper-detailed fantasy/cinematic scene",
        research_angle="Extract the core dramatic conflict, identifying the specific inciting incident and human cost at the center",
        target_wpm=140,
        subtitle_font="Impact",
        primary_color_rgb=(255, 220, 100),
        outline_color_rgb=(15, 15, 15),
    ),
    ContentStyle.KIDS_STORY: StyleProfile(
        name="Kids Story",
        script_prompt=(
            "Write a highly engaging, cognitively optimized script for young audiences. Employ rhythmic rhyming structures, "
            "repetitive learning anchors, and highly visual, optimistic language with a clear moral lesson."
        ),
        tts_cadence_cue="(Speaking with hyper-animated, exuberant energy. Highly melodic intonation, exaggerated expressions of surprise and joy)",
        video_aesthetic="High-budget 3D animation (Pixar/Disney aesthetic), vibrant hyper-saturated primary colors, bouncy fluid motion, soft plush textures",
        image_prompt_suffix="premium 3D CGI render, adorable character designs, bright cheerful lighting, pastel palette, magical atmosphere",
        research_angle="Identify foundational educational concepts and translate them into playful analogies",
        target_wpm=125,
        subtitle_font="Comic Sans MS",
        primary_color_rgb=(255, 240, 80),
        outline_color_rgb=(0, 0, 0),
    ),
    ContentStyle.HORROR: StyleProfile(
        name="Horror Story",
        script_prompt=(
            "Engineer a narrative of psychological terror. Utilize the 'slow burn' technique, dripping with existential dread. "
            "Focus on the uncanny valley, isolation, and sensory deprivation. Avoid cheap tropes in favor of lingering descriptive dread."
        ),
        tts_cadence_cue="(Speaking with a hollow, breathy, and deeply sinister undertone. Erratic pacing, sudden drops to a whisper)",
        video_aesthetic="A24-style psychological horror cinematography, extreme low-key lighting, heavy film grain, unsettling Dutch angles, sickly green/amber tint",
        image_prompt_suffix="macabre fine-art photography, terrifying surrealism, liminal spaces, extreme shadows, muted desolate tones",
        research_angle="Uncover the most disturbing, unsolved, or psychologically chilling historical facts and folklore",
        target_wpm=120,
        subtitle_font="Impact",
        primary_color_rgb=(255, 60, 60),
        outline_color_rgb=(0, 0, 0),
    ),
    ContentStyle.VIRAL_VIDEO: StyleProfile(
        name="Viral Video",
        script_prompt=(
            "Optimize for maximum algorithmic retention (TikTok/Shorts). Deploy an aggressive pattern-interrupt hook in the first 3 seconds. "
            "Utilize rapid-fire delivery, relentless curiosity gaps, and high-stakes payoffs."
        ),
        tts_cadence_cue="(Speaking with relentless, high-octane energy. Fast-paced, punchy, zero dead air, projecting absolute confidence and urgency)",
        video_aesthetic="Hyper-kinetic social media editing style, rapid snap-zooms, aggressive motion graphics, glowing neon accents, high contrast",
        image_prompt_suffix="ultra-vibrant high CTR aesthetic, glowing neon outlines, dynamic dramatic angles, maximum clarity",
        research_angle="Identify the absolute most shocking, counter-intuitive, or controversial 'secret' that shatters common belief",
        target_wpm=170,
        subtitle_font="Impact",
        primary_color_rgb=(255, 255, 0),
        outline_color_rgb=(0, 0, 0),
    ),
    ContentStyle.PRODUCT_AD: StyleProfile(
        name="Product Ad",
        script_prompt=(
            "Engineer a high-converting direct-response script using the AIDA framework (Attention, Interest, Desire, Action). "
            "Agitate a specific pain point intensely before revealing the solution as an exclusive game-changer."
        ),
        tts_cadence_cue="(Speaking with magnetic, authoritative sales charisma. Smooth, persuasive, confident, and inherently trustworthy)",
        video_aesthetic="Premium commercial cinematography (Apple/Nike aesthetic), sleek minimalist backgrounds, macroscopic product beauty shots, buttery slow-motion",
        image_prompt_suffix="commercial studio product photography, razor-sharp focus, infinite clean background, dramatic rim lighting",
        research_angle="Determine core buyer psychology, specific emotional pain points, and unique value proposition",
        target_wpm=150,
        subtitle_font="Arial Black",
        primary_color_rgb=(255, 255, 255),
        outline_color_rgb=(30, 30, 30),
    ),
    ContentStyle.STOIC_FACTS: StyleProfile(
        name="Stoic Facts",
        script_prompt=(
            "Deliver timeless philosophical axioms with stoic precision. Every sentence should feel carved in marble. "
            "Reject sensationalism; embrace brutal honesty and calm resilience."
        ),
        tts_cadence_cue="(Calm, unflinching, deep resonance with deliberate pauses after pivotal philosophical statements)",
        video_aesthetic="Classical statue cinematography, dramatic side-lighting on ancient marble bust, slow vertical pan, monochrome moody tone",
        image_prompt_suffix="ancient Roman marble bust of Marcus Aurelius, dramatic chiaroscuro museum lighting, classical sculpture texture",
        research_angle="Extract core teachings from Seneca, Marcus Aurelius, Epictetus applied to modern psychological dilemmas",
        target_wpm=130,
        subtitle_font="Georgia",
        primary_color_rgb=(240, 235, 220),
        outline_color_rgb=(20, 20, 20),
    ),
}


class StyleProfileManager:
    """Manages content style presets and enriches prompts, TTS, and visuals."""

    def __init__(self, default_style: ContentStyle = ContentStyle.VIRAL_VIDEO):
        self.default_style = default_style

    def resolve_style(self, style_input: Union[str, ContentStyle, None]) -> ContentStyle:
        if not style_input:
            return self.default_style
        if isinstance(style_input, ContentStyle):
            return style_input

        clean = str(style_input).lower().strip().replace(" ", "_").replace("-", "_")
        for key in ContentStyle:
            if key.value == clean or key.name.lower() == clean:
                return key

        # Partial matching keywords
        if "asmr" in clean:
            return ContentStyle.ASMR
        if "horror" in clean or "scary" in clean or "korku" in clean:
            return ContentStyle.HORROR
        if "kid" in clean or "çocuk" in clean:
            return ContentStyle.KIDS_STORY
        if "doc" in clean or "belgesel" in clean:
            return ContentStyle.DOCUMENTARY
        if "podcast" in clean or "sohbet" in clean:
            return ContentStyle.PODCAST
        if "stoic" in clean or "felsefe" in clean or "stoa" in clean:
            return ContentStyle.STOIC_FACTS
        if "ad" in clean or "product" in clean or "reklam" in clean:
            return ContentStyle.PRODUCT_AD
        if "story" in clean or "hikaye" in clean:
            return ContentStyle.STORY

        return self.default_style

    def get_profile(self, style_input: Union[str, ContentStyle, None]) -> StyleProfile:
        resolved = self.resolve_style(style_input)
        return STYLE_PROFILES.get(resolved, STYLE_PROFILES[ContentStyle.VIRAL_VIDEO])

    def enrich_script_prompt(self, base_prompt: str, style_input: Union[str, ContentStyle, None]) -> str:
        profile = self.get_profile(style_input)
        return (
            f"{base_prompt}\n\n"
            f"[STYLE PROFILE: {profile.name}]\n"
            f"Script Formula: {profile.script_prompt}\n"
            f"Research Directives: {profile.research_angle}\n"
            f"Target Cadence: ~{profile.target_wpm} words/minute"
        )

    def enrich_visual_prompt(self, scene_description: str, style_input: Union[str, ContentStyle, None]) -> str:
        profile = self.get_profile(style_input)
        return f"{scene_description}, {profile.video_aesthetic}, {profile.image_prompt_suffix}"

    def get_tts_config(self, style_input: Union[str, ContentStyle, None]) -> Dict[str, Any]:
        profile = self.get_profile(style_input)
        return {
            "style_name": profile.name,
            "cadence_cue": profile.tts_cadence_cue,
            "target_wpm": profile.target_wpm,
        }

    def get_subtitle_theme(self, style_input: Union[str, ContentStyle, None]) -> Dict[str, Any]:
        profile = self.get_profile(style_input)
        return {
            "font": profile.subtitle_font,
            "primary_color": profile.primary_color_rgb,
            "outline_color": profile.outline_color_rgb,
        }


style_profile_manager = StyleProfileManager()
