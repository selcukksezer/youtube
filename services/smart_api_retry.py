"""
Smart API Quota & Rate-Limit Retry Handler.
Adapted and enhanced from naqashafzal/AI-Content-Studio (api_clients.py).
Parses precise quota error messages (e.g. 'Please retry in Xs' from Gemini / Vertex AI,
HTTP 429 Retry-After headers) and executes intelligent backoff to prevent pipeline crashes.
"""
import functools
import logging
import random
import re
import time
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union

logger = logging.getLogger(__name__)


def parse_retry_after(error: Union[Exception, str]) -> Optional[float]:
    """
    Extracts explicit retry-after wait duration in seconds from exception or error string.
    Works for Google Gemini ('Please retry in 18.23s'), HTTP 429 headers, or rate limits.
    """
    msg = str(error)
    # Pattern 1: Gemini/Vertex: "Please retry in 12.4s" or "Please retry in 15s"
    m1 = re.search(r"[Pp]lease retry in\s+([0-9]+(?:\.[0-9]+)?)\s*s", msg)
    if m1:
        return float(m1.group(1))

    # Pattern 2: HTTP Retry-After format: "Retry-After:\s*([0-9]+)"
    m2 = re.search(r"[Rr]etry-[Aa]fter[:=]\s*([0-9]+)", msg)
    if m2:
        return float(m2.group(1))

    # Pattern 3: "rate limit exceeded... wait ([0-9]+) seconds"
    m3 = re.search(r"wait\s+([0-9]+(?:\.[0-9]+)?)\s*(?:sec|second|s)", msg, re.IGNORECASE)
    if m3:
        return float(m3.group(1))

    return None


def is_rate_limit_error(error: Exception) -> bool:
    """Detects if exception represents a rate limit / quota exhaustion event."""
    msg = str(error).lower()
    error_type = type(error).__name__.lower()

    if "resourceexhausted" in error_type or "resourceexhausted" in msg:
        return True
    if "ratelimit" in error_type or "ratelimit" in msg:
        return True
    if "429" in msg or "too many requests" in msg:
        return True
    if "quota exceeded" in msg or "quota_exceeded" in msg:
        return True
    return False


def robust_api_call(
    max_retries: int = 4,
    base_wait_sec: float = 2.0,
    max_wait_sec: float = 60.0,
    fallback_value: Any = None,
    reraise_on_exhaust: bool = True,
):
    """
    Decorator that catches rate-limit and transient API errors, dynamically waits
    the recommended or exponential time with jitter, and retries.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    if attempt == max_retries:
                        break

                    if is_rate_limit_error(e):
                        suggested = parse_retry_after(e)
                        if suggested is not None and suggested > 0:
                            wait_time = min(suggested + 1.0 + random.uniform(0.1, 0.5), max_wait_sec)
                            logger.warning(
                                f"[{func.__name__}] Rate limit parsed: sleeping {wait_time:.1f}s "
                                f"(attempt {attempt + 1}/{max_retries})"
                            )
                        else:
                            wait_time = min(
                                base_wait_sec * (2 ** attempt) + random.uniform(0.2, 1.0),
                                max_wait_sec
                            )
                            logger.warning(
                                f"[{func.__name__}] Rate limit hit: exponential backoff {wait_time:.1f}s "
                                f"(attempt {attempt + 1}/{max_retries})"
                            )
                        time.sleep(wait_time)
                    else:
                        # Non-rate-limit error (e.g. transient 500/503 network drop)
                        msg = str(e).lower()
                        if any(term in msg for term in ("503", "502", "504", "connection", "timeout")):
                            wait_time = min(base_wait_sec * (1.5 ** attempt), 10.0)
                            logger.warning(
                                f"[{func.__name__}] Transient network error: sleeping {wait_time:.1f}s"
                            )
                            time.sleep(wait_time)
                        else:
                            # Not a transient/rate-limit error, re-raise immediately
                            raise e

            logger.error(f"[{func.__name__}] Exhausted all {max_retries} retries: {last_err}")
            if reraise_on_exhaust:
                raise last_err
            return fallback_value

        return wrapper

    return decorator
