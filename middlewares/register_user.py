from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from services import db


class RegisterUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update):
            user = None
            if event.message:
                user = event.message.from_user
            elif event.callback_query:
                user = event.callback_query.from_user

            if user:
                await db.upsert_user(user.id, user.username)

        return await handler(event, data)
