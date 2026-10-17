"""
Static Niche Catalog Data, Scene Format Templates, Outro CTAs, and English Hooks/Instructions.
Extracted from niche_templates.py for modular maintainability.
"""
from typing import Dict, Any

from .niche_catalog_part1 import NICHES_PART1
from .niche_catalog_part2 import NICHES_PART2
from .niche_catalog_part3 import SCENE_FORMAT_TEMPLATES, NICHE_OUTRO_CTA

# 37 Niche definitions — full production schema
NICHES: Dict[str, Dict[str, Any]] = {
    **NICHES_PART1,
    **NICHES_PART2,
}

NICHE_HOOKS_EN: Dict[str, str] = {
    "1_news_flash": "Something critical just happened that changes everything...",
    "2_reddit_confessions": "I never planned on telling a soul, but last night everything fell apart...",
    "3_split_gameplay": "Watch closely, because what happened next completely defies logic...",
    "4_would_you_rather": "Only 1% of people can make this choice without hesitating...",
    "5_guess_flag_country": "Can you guess this mystery country before the timer runs out?",
    "6_stoic_philosophy": "Marcus Aurelius had a brutal rule for anger that most people never learn...",
    "7_dark_psychology": "If someone looks you in the eyes like this, they are manipulating you...",
    "8_crypto_market": "While retail investors panic, crypto whales are making this exact move...",
    "9_five_facts": "5 mind-blowing facts that will completely alter how you see reality...",
    "10_religious_quotes": "If your heart is feeling heavy, remember this powerful truth...",
    "11_language_learning": "Stop saying 'very' in English — use these 5 advanced alternatives...",
    "12_amazon_affiliate": "This viral Amazon gadget solves a problem you deal with every single day...",
    "13_mystery_paranormal": "Even modern science cannot explain what happened in this bizarre event...",
    "14_movie_summaries": "The ending of this psychological thriller will leave your mind completely blown...",
    "15_football_transfers": "This single transfer decision changed football history forever...",
    "16_wealth_entrepreneurship": "The wealthiest 1% follow one simple rule with money that schools never teach...",
    "17_before_after_evolution": "You won't believe how much our world has transformed over the last 100 years...",
    "18_astrology_horoscope": "Never push these 3 zodiac signs to their absolute limit...",
    "19_historical_battles": "How a vastly outnumbered army pulled off the greatest victory in history...",
    "20_whatsapp_chat_story": "These creepy 3 AM text messages will send absolute chills down your spine...",
    "21_ai_tools_hacks": "3 secret AI tools that are so powerful they almost feel illegal to use...",
    "22_emoji_guess_game": "Can you guess this legendary movie using only these 3 emojis?",
    "23_fitness_nutrition_hacks": "The science-backed morning habit that burns stubborn fat without starving...",
    "24_sigma_character_study": "The quiet psychological rule that makes a high-value mindset untouchable...",
    "25_celebrity_net_worth": "How much money this superstar actually takes home after taxes will shock you...",
    "26_dangerous_places": "The forbidden island on Earth that no human is allowed to visit...",
    "27_common_myths_busted": "5 popular myths everyone still believes that are completely false...",
    "28_dream_meanings": "What it actually means when you dream of falling from great heights...",
    "29_optical_illusions_iq": "Only people with 130+ IQ can spot the hidden animal in 5 seconds...",
    "30_poetry_quotes": "The hauntingly beautiful quote about heartbreak that you will never forget...",
    "31_supercars_automotive": "The insane secret engineering that allows this hypercar to reach 300 MPH...",
    "32_legal_consumer_hacks": "3 hidden consumer rights that major companies hide in the fine print...",
    "33_parenting_child_hacks": "The 3-second phrase child psychologists use to stop tantrums instantly...",
    "34_gaming_easter_eggs": "5 terrifying video game secrets that took players over a decade to discover...",
    "35_animal_kingdom_stories": "The deadliest predator in the animal kingdom is not what you think...",
    "36_kids_animation": "Join our adorable animal friends on a magical learning adventure!",
    "37_interactive_quiz": "95% of adults fail question number 3 on this general knowledge test...",
}


NICHE_INSTRUCTIONS_EN: Dict[str, str] = {
    "1_news_flash": "Deliver urgent, breaking global developments with rapid pace, journalistic clarity, and cinematic authority.",
    "2_reddit_confessions": "Narrate an authentic first-person confession with emotional suspense, dramatic twists, and relatable tension.",
    "3_split_gameplay": "Deliver a captivating, eerie, or fascinating story designed to keep the viewer glued from start to finish.",
    "4_would_you_rather": "Present impossible moral dilemmas and polarizing choices that compel viewers to debate in the comments.",
    "5_guess_flag_country": "Deliver an intense, fast-paced trivia challenge with 3 progressive clues before revealing the mystery country.",
    "6_stoic_philosophy": "Explain timeless Stoic principles from Marcus Aurelius or Seneca focusing on emotional mastery and inner resilience.",
    "7_dark_psychology": "Deconstruct dark psychological tactics, body language tells, and subtle manipulation techniques people face daily.",
    "8_crypto_market": "Analyze high-stakes cryptocurrency moves, on-chain whale behavior, and market psychology with objective urgency.",
    "9_five_facts": "Present mind-blowing, verified scientific or historical facts with rapid-fire clarity and high visual contrast.",
    "10_religious_quotes": "Share authentic spiritual wisdom, Quranic verses, or Hadiths that bring deep peace and moral clarity to the soul.",
    "11_language_learning": "Teach advanced vocabulary, native idioms, and fluency secrets that traditional classrooms never explain.",
    "12_amazon_affiliate": "Demonstrate viral, life-improving gadgets with compelling problem-solution framing and clear practical value.",
    "13_mystery_paranormal": "Investigate unsolved historical enigmas, eerie vanishings, and chilling true events with gripping suspense.",
    "14_movie_summaries": "Break down jaw-dropping movie plot twists, hidden cinematic details, and psychological thrillers without cheap spoilers.",
    "15_football_transfers": "Cover shocking football transfers, legendary tactical masterstrokes, and drama from the world of elite football.",
    "16_wealth_entrepreneurship": "Deconstruct the ruthless work ethics, business philosophies, and money rules of self-made billionaires.",
    "17_before_after_evolution": "Showcase dramatic historical contrasts and technological evolutions that highlight how the world has changed.",
    "18_astrology_horoscope": "Explore deep astrological traits, subconscious zodiac powers, and behavioral dynamics with engaging mystery.",
    "19_historical_battles": "Narrate epic military strategies, against-all-odds triumphs, and turning points in ancient and modern warfare.",
    "20_whatsapp_chat_story": "Narrate a chilling, suspenseful text message exchange with rising dread and an unexpected cliffhanger.",
    "21_ai_tools_hacks": "Highlight powerful, game-changing AI tools that boost productivity and automate complex workflows.",
    "22_emoji_guess_game": "Challenge viewers to guess iconic movies using only 3 emojis with tight time pressure.",
    "23_fitness_nutrition_hacks": "Provide science-backed fat loss, muscle building, and nutrition hacks that deliver fast, realistic results.",
    "24_sigma_character_study": "Break down the psychological traits, quiet confidence, and independence of the sigma archetype.",
    "25_celebrity_net_worth": "Reveal the real net worth, spending habits, and behind-the-scenes financial moves of famous celebrities.",
    "26_dangerous_places": "Take viewers inside the most dangerous, forbidden, and hostile locations on Earth that humans cannot visit.",
    "27_common_myths_busted": "Debunk widespread historical, scientific, or cultural myths with definitive evidence.",
    "28_dream_meanings": "Decode the psychological and subconscious meanings behind common, vivid, and recurring dreams.",
    "29_optical_illusions_iq": "Present mind-bending optical illusions and cognitive IQ tests that challenge visual perception.",
    "30_poetry_quotes": "Share deeply emotional, poignant poetry and timeless literary quotes on love, resilience, and longing.",
    "31_supercars_automotive": "Explore cutting-edge engineering secrets, insane top speeds, and performance specs of elite hypercars.",
    "32_legal_consumer_hacks": "Expose secret consumer rights, airline loopholes, and legal protections that save money.",
    "33_parenting_child_hacks": "Share practical child psychology techniques and calm parenting strategies that defuse difficult moments.",
    "34_gaming_easter_eggs": "Uncover disturbing, hilarious, or secret easter eggs hidden deep within beloved video games.",
    "35_animal_kingdom_stories": "Tell incredible stories of survival, deadly animal rivalries, and shocking wildlife behaviors.",
    "36_kids_animation": "Craft delightful, educational, and fun narratives for young children teaching colors, animals, or morals.",
    "37_interactive_quiz": "Run an interactive multiple-choice general knowledge quiz that engages viewers to guess and comment.",
}

__all__ = [
    "NICHES",
    "NICHES_PART1",
    "NICHES_PART2",
    "SCENE_FORMAT_TEMPLATES",
    "NICHE_OUTRO_CTA",
    "NICHE_HOOKS_EN",
    "NICHE_INSTRUCTIONS_EN",
]
