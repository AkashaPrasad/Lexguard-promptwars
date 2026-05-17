"""Gemini API client — async-native, semaphore-protected, returns raw JSON string."""
import asyncio
import hashlib
import logging
from typing import Optional

from config import GEMINI_API_KEY, GEMINI_MODEL_FLASH

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig

    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
        logger.info("Gemini configured with model %s", GEMINI_MODEL_FLASH)
    else:
        GEMINI_AVAILABLE = False
        logger.warning("GEMINI_API_KEY not set — Gemini unavailable")
except ImportError:
    GEMINI_AVAILABLE = False
    logger.error("google-generativeai package not installed")

_response_cache: dict = {}
_semaphore: Optional[asyncio.Semaphore] = None
_CONCURRENCY_LIMIT = 8  # max simultaneous Gemini API calls


def _get_semaphore() -> asyncio.Semaphore:
    """Lazily create semaphore once an event loop is running."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_CONCURRENCY_LIMIT)
    return _semaphore


def _cache_key(model_name: str, prompt: str) -> str:
    return hashlib.sha256(f"{model_name}:{prompt}".encode()).hexdigest()


def _strip_fences(text: str) -> str:
    """Remove markdown code fences that Gemini sometimes adds."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
    return text.strip()


def _extract_text(response) -> str:
    """Safely extract text from a Gemini response, raising on blocked/empty."""
    if not response.candidates:
        raise ValueError(
            "Gemini response has no candidates — response may have been blocked by safety filters"
        )
    candidate = response.candidates[0]
    finish = str(getattr(candidate, "finish_reason", "")).upper()
    if finish in ("SAFETY", "RECITATION", "OTHER") or not candidate.content.parts:
        raise ValueError(f"Gemini response was blocked or incomplete (finish_reason={finish})")
    text = _strip_fences(response.text.strip())
    if not text:
        raise ValueError("Gemini returned an empty response")
    return text


async def call_gemini(
    prompt: str,
    model_name: str = GEMINI_MODEL_FLASH,
    temperature: float = 0.1,
    max_retries: int = 4,
) -> str:
    """Call Gemini API using native async and return the raw JSON string.

    Uses generate_content_async() — no thread pool, no event loop blocking.
    Semaphore limits concurrency to avoid flooding the API.
    Raises RuntimeError if Gemini is not configured or all retries fail.
    """
    if not GEMINI_AVAILABLE:
        raise RuntimeError(
            "Gemini API not configured — set GEMINI_API_KEY environment variable"
        )

    key = _cache_key(model_name, prompt)
    if key in _response_cache:
        return _response_cache[key]

    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )

    sem = _get_semaphore()
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            async with sem:
                response = await asyncio.wait_for(
                    model.generate_content_async(prompt),
                    timeout=60.0,
                )
            text = _extract_text(response)
            _response_cache[key] = text
            logger.debug("Gemini OK (attempt %d/%d, model=%s)", attempt + 1, max_retries, model_name)
            return text

        except asyncio.TimeoutError as e:
            last_error = e
            wait = 5 * (attempt + 1)
            logger.warning("Gemini timeout (attempt %d/%d) — retry in %ds", attempt + 1, max_retries, wait)

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            is_quota = any(
                x in err_str
                for x in ("429", "quota", "resource_exhausted", "rate limit", "resourceexhausted")
            )
            wait = (2**attempt) * (5 if is_quota else 2)
            logger.warning(
                "Gemini failed (attempt %d/%d, %s): %.120s — retry in %ds",
                attempt + 1,
                max_retries,
                "QUOTA" if is_quota else "ERROR",
                e,
                wait,
            )

        if attempt < max_retries - 1:
            await asyncio.sleep(wait)

    raise RuntimeError(
        f"Gemini failed after {max_retries} attempts: {last_error}"
    ) from last_error
