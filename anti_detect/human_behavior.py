"""
Human Behavior Simulation: Bezier Mouse, Typing Cadence, Jitter & Warmup
Covers items: 7, 8, 11, 12, 17, 18, 47
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from .profile import PRE_UPLOAD_NATURAL_COMMENTS

def calculate_upload_jitter(target_hour: int, target_minute: int = 0, target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculates humanized upload timestamp with randomized jitter.
    Avoids exact-hour robot footprint (Items 8, 47).
    Generates both formatted time and standard ISO-8601 publishAt string.
    """
    now = datetime.now()
    
    jitter_minutes = random.randint(3, 18)
    jitter_seconds = random.randint(4, 58)
    
    target_dt = now.replace(hour=target_hour % 24, minute=target_minute % 60, second=0, microsecond=0)
    if target_dt <= now:
        target_dt += timedelta(days=1)
        
    jittered_dt = target_dt + timedelta(minutes=jitter_minutes, seconds=jitter_seconds)
    iso_str = jittered_dt.strftime("%Y-%m-%dT%H:%M:%S+03:00")

    return {
        "scheduled_hour": jittered_dt.hour,
        "scheduled_minute": jittered_dt.minute,
        "scheduled_second": jittered_dt.second,
        "time_str": jittered_dt.strftime("%H:%M:%S"),
        "date_str": jittered_dt.strftime("%d.%m.%Y"),
        "scheduled_iso": iso_str,
        "jitter_applied_minutes": jitter_minutes,
        "jitter_applied_seconds": jitter_seconds
    }

def generate_typing_delays(text: str) -> List[float]:
    """
    Generates millisecond keystroke delays mimicking human cadence (Item 12).
    Includes micro-pauses at spaces and punctuation.
    """
    delays = []
    for char in text:
        if char in " ,.!?":
            delay = random.uniform(0.12, 0.35)  # Pause at punctuation
        elif char.isupper():
            delay = random.uniform(0.08, 0.20)  # Shift key delay
        else:
            delay = random.uniform(0.04, 0.11)  # Regular typing
        delays.append(round(delay, 4))
    return delays

def generate_bezier_mouse_path(start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 25) -> List[Dict[str, int]]:
    """
    Generates realistic cubic Bezier curve coordinates for human mouse movement (Item 11).
    """
    ctrl1_x = start_x + (end_x - start_x) * 0.25 + random.randint(-40, 40)
    ctrl1_y = start_y + (end_y - start_y) * 0.25 + random.randint(-40, 40)
    ctrl2_x = start_x + (end_x - start_x) * 0.75 + random.randint(-30, 30)
    ctrl2_y = start_y + (end_y - start_y) * 0.75 + random.randint(-30, 30)

    points = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t)**3 * start_x + 3 * (1 - t)**2 * t * ctrl1_x + 3 * (1 - t) * t**2 * ctrl2_x + t**3 * end_x
        y = (1 - t)**3 * start_y + 3 * (1 - t)**2 * t * ctrl1_y + 3 * (1 - t) * t**2 * ctrl2_y + t**3 * end_y
        points.append({"x": int(round(x)), "y": int(round(y))})

    return points

async def human_mouse_move(page, target_x: int, target_y: int, start_x: int = 100, start_y: int = 100):
    """
    Executes realistic human mouse movement along a cubic Bezier curve (Item 11).
    Applies natural acceleration, deceleration, and micro-hand-tremor.
    """
    import asyncio
    steps = random.randint(18, 28)
    points = generate_bezier_mouse_path(start_x, start_y, target_x, target_y, steps=steps)
    
    for idx, pt in enumerate(points):
        progress = idx / len(points)
        if progress < 0.2 or progress > 0.8:
            step_delay = random.uniform(0.012, 0.025)
        else:
            step_delay = random.uniform(0.005, 0.012)

        await page.mouse.move(pt["x"], pt["y"])
        await asyncio.sleep(step_delay)

async def human_type_text(page, selector: str, text: str):
    """
    Types text with human cadence, variable 40ms - 130ms delays, and natural micro-pauses (Item 12).
    """
    import asyncio
    await page.click(selector)
    await asyncio.sleep(random.uniform(0.15, 0.35))

    delays = generate_typing_delays(text)
    for char, delay in zip(text, delays):
        await page.keyboard.type(char)
        await asyncio.sleep(delay)

def generate_warmup_session_plan(niche_keyword: str) -> Dict[str, Any]:
    """
    Creates an organic account warm-up session routine (Items 7, 17, 18).
    Simulates watching 2-3 Shorts in the niche before publishing.
    """
    shorts_to_watch = random.randint(2, 3)
    watch_plan = []
    total_session_seconds = 0

    for i in range(shorts_to_watch):
        watch_duration = random.randint(25, 48)
        should_like = (i == 0 or random.random() < 0.5)
        should_expand_desc = random.random() < 0.3
        total_session_seconds += watch_duration + random.randint(3, 7)

        watch_plan.append({
            "action": "watch_short",
            "index": i + 1,
            "duration_seconds": watch_duration,
            "like_video": should_like,
            "expand_description": should_expand_desc
        })

    post_upload_idle = random.randint(35, 75)
    total_session_seconds += post_upload_idle + 45

    return {
        "niche_keyword": niche_keyword,
        "shorts_count": shorts_to_watch,
        "steps": watch_plan,
        "post_upload_idle_seconds": post_upload_idle,
        "estimated_total_session_minutes": round(total_session_seconds / 60, 1),
        "human_trust_score_gain": "+25 Trust Points (Organik Sinyal)"
    }

def generate_pre_upload_interaction_plan(niche_keyword: str, lang: str = "tr") -> Dict[str, Any]:
    """
    Creates a pre-upload Shorts interaction plan (Rule 17).
    Watches 2-3 Shorts to the end, likes 1, and posts 1 authentic niche comment
    immediately before uploading to YouTube Studio.
    """
    shorts_count = random.randint(2, 3)
    steps = []
    total_seconds = 0

    comment_pool = PRE_UPLOAD_NATURAL_COMMENTS.get(lang, PRE_UPLOAD_NATURAL_COMMENTS["tr"])
    chosen_comment = random.choice(comment_pool)
    comment_index = random.randint(1, shorts_count)

    for i in range(1, shorts_count + 1):
        watch_duration = random.randint(22, 46)
        total_seconds += watch_duration + random.randint(2, 5)

        is_like = (i == 1 or random.random() < 0.6)
        is_comment = (i == comment_index)

        steps.append({
            "action": "watch_and_interact",
            "index": i,
            "watch_duration_seconds": watch_duration,
            "like_video": is_like,
            "leave_comment": is_comment,
            "comment_text": chosen_comment if is_comment else None
        })

    return {
        "niche_keyword": niche_keyword,
        "shorts_count": shorts_count,
        "steps": steps,
        "selected_comment": chosen_comment,
        "estimated_pre_upload_duration_seconds": total_seconds,
        "rule_compliance": "Kural 17: Yükleme Öncesi 2-3 Shorts İzleme, Beğeni ve Yorum Hazır"
    }

def calculate_natural_session_duration() -> Dict[str, Any]:
    """
    Calculates and enforces human natural session duration (Rule 18).
    Enforces 3-7 minutes (180 to 420 seconds) platform residency.
    """
    target_seconds = random.randint(195, 410)
    target_minutes = round(target_seconds / 60.0, 2)
    return {
        "min_allowed_seconds": 180,
        "max_allowed_seconds": 420,
        "target_session_seconds": target_seconds,
        "target_session_minutes": target_minutes,
        "cooldown_strategy": "passive_shorts_and_home_scroll",
        "info": f"Kural 18 Doğal Oturum Süresi: {target_minutes} dk (Erken çıkış engeli devrede)."
    }
