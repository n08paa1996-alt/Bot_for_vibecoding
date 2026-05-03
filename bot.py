import asyncio
import logging
import structlog
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import settings
from middlewares import RegisterUserMiddleware, RateLimitMiddleware
from services import db, knowledge_base, openrouter
from handlers import start, tz_wizard, visual, claude_base, deploy


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(message)s",
    )


log = structlog.get_logger()


async def on_startup(bot: Bot) -> None:
    import os
    os.makedirs("data", exist_ok=True)
    await db.init_db()
    knowledge_base.load()

    if settings.WEBHOOK_HOST:
        webhook_url = f"{settings.WEBHOOK_HOST}{settings.WEBHOOK_PATH}"
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        log.info("webhook_set", url=webhook_url)
    else:
        log.info("polling_mode")


async def on_shutdown(bot: Bot) -> None:
    await openrouter.close_session()
    if settings.WEBHOOK_HOST:
        await bot.delete_webhook()
    log.info("bot_shutdown")


def build_app() -> web.Application:
    configure_logging()

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.update.outer_middleware(RegisterUserMiddleware())
    dp.update.outer_middleware(RateLimitMiddleware())

    dp.include_router(tz_wizard.router)
    dp.include_router(visual.router)
    dp.include_router(claude_base.router)
    dp.include_router(deploy.router)
    dp.include_router(start.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    async def health(request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app.router.add_get("/health", health)

    if settings.WEBHOOK_HOST:
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=settings.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
    else:
        async def run_polling(_app: web.Application) -> None:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

        app.on_startup.append(run_polling)

    return app


async def main() -> None:
    if settings.WEBHOOK_HOST:
        app = build_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=8080)
        await site.start()
        log.info("server_started", port=8080)
        await asyncio.Event().wait()
    else:
        configure_logging()
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        dp.update.outer_middleware(RegisterUserMiddleware())
        dp.update.outer_middleware(RateLimitMiddleware())

        dp.include_router(tz_wizard.router)
        dp.include_router(visual.router)
        dp.include_router(claude_base.router)
        dp.include_router(deploy.router)
        dp.include_router(start.router)

        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
