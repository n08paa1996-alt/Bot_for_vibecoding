from services import openrouter

SYSTEM_PROMPT = (
    "Ты профессиональный промпт-инженер для генерации изображений (Stable Diffusion, Flux, DALL-E). "
    "Твоя задача — улучшить пользовательский промпт, добавив: "
    "стиль, освещение, детализацию, технические параметры, композицию. "
    "Сделай промпт на английском языке. "
    "Верни ТОЛЬКО улучшенный промпт — без объяснений, без вводных фраз, без кавычек."
)


async def enhance_image_prompt(user_prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Улучши этот промпт: {user_prompt}"},
    ]
    result, _ = await openrouter.chat(messages, max_tokens=300, temperature=0.8)
    return result.strip()
