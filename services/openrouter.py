import asyncio
import aiohttp
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import structlog

from config import settings

log = structlog.get_logger()

_session: aiohttp.ClientSession | None = None
_image_session: aiohttp.ClientSession | None = None
_image_semaphore: asyncio.Semaphore | None = None

FALLBACK_IMAGE_MODEL = "openai/dall-e-3"


def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://vibemaster-ai.bot",
                "X-Title": "VibeMaster AI",
                "Content-Type": "application/json",
            }
        )
    return _session


def get_image_session() -> aiohttp.ClientSession:
    global _image_session
    if _image_session is None or _image_session.closed:
        _image_session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {settings.effective_image_api_key}",
                "HTTP-Referer": "https://vibemaster-ai.bot",
                "X-Title": "VibeMaster AI",
                "Content-Type": "application/json",
            }
        )
    return _image_session


def get_image_semaphore() -> asyncio.Semaphore:
    global _image_semaphore
    if _image_semaphore is None:
        _image_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_IMAGE_TASKS)
    return _image_semaphore


async def close_session() -> None:
    global _session, _image_session
    if _session and not _session.closed:
        await _session.close()
    if _image_session and not _image_session.closed:
        await _image_session.close()


class OpenRouterError(Exception):
    pass


class RateLimitError(OpenRouterError):
    pass


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(RateLimitError),
    reraise=True,
)
async def chat(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> tuple[str, int]:
    model = model or settings.DEFAULT_TEXT_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    timeout = aiohttp.ClientTimeout(total=60)
    session = get_session()
    try:
        async with session.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            timeout=timeout,
        ) as resp:
            if resp.status == 429:
                await asyncio.sleep(3)
                raise RateLimitError("Rate limit hit")
            if resp.status != 200:
                text = await resp.text()
                raise OpenRouterError(f"API error {resp.status}: {text[:200]}")
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return content, tokens
    except aiohttp.ClientError as e:
        raise OpenRouterError(f"Network error: {e}") from e


async def generate_image(prompt: str, model: str | None = None) -> bytes:
    """Генерирует изображение через Pollinations.AI — бесплатный публичный API без ключей.
    GET https://image.pollinations.ai/prompt/{encoded_prompt}
    """
    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=flux&nologo=true&seed={asyncio.get_event_loop().time().__int__()}"
    timeout = aiohttp.ClientTimeout(total=120)

    async with get_image_semaphore():
        try:
            # Pollinations не требует авторизации — используем чистую сессию
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        log.warning("pollinations_failed", status=resp.status, body=text[:200])
                        raise OpenRouterError(f"Image generation failed: {resp.status}")
                    return await resp.read()
        except aiohttp.ClientError as e:
            raise OpenRouterError(f"Network error: {e}") from e
