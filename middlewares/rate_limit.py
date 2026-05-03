import time
from collections import deque
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery

WINDOW_SECONDS = 10
MAX_REQUESTS = 10


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._user_timestamps: dict[int, deque] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = self._get_user_id(event)
        if user_id and self._is_rate_limited(user_id):
            if isinstance(event, Update):
                msg = event.message or (
                    event.callback_query.message if event.callback_query else None
                )
                if msg:
                    await msg.answer("⏳ Подожди немного — ты отправляешь слишком много сообщений.")
            return

        return await handler(event, data)

    def _get_user_id(self, event: TelegramObject) -> int | None:
        if isinstance(event, Update):
            if event.message:
                return event.message.from_user.id
            if event.callback_query:
                return event.callback_query.from_user.id
        return None

    def _is_rate_limited(self, user_id: int) -> bool:
        now = time.monotonic()
        if user_id not in self._user_timestamps:
            self._user_timestamps[user_id] = deque()

        dq = self._user_timestamps[user_id]
        while dq and now - dq[0] > WINDOW_SECONDS:
            dq.popleft()

        if len(dq) >= MAX_REQUESTS:
            return True

        dq.append(now)
        return False
