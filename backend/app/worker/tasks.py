from arq import cron
from redis.asyncio import Redis

from app.config import settings
from app.database import async_session
from app.services.crypto import CryptoService
from app.worker.token_checker import check_tokens


async def run_token_check(ctx):
    crypto = CryptoService(settings.ENCRYPTION_KEY)
    redis = ctx.get("redis") or Redis.from_url(settings.REDIS_URL, decode_responses=False)
    await check_tokens(
        async_session,
        crypto,
        redis,
        interval=settings.TOKEN_CHECK_INTERVAL,
        concurrency=settings.TOKEN_CHECK_CONCURRENCY,
    )


class WorkerSettings:
    functions = []
    cron_jobs = [
        cron(run_token_check, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
    redis_settings = None

    @staticmethod
    def on_startup(ctx):
        ctx["redis"] = Redis.from_url(settings.REDIS_URL, decode_responses=False)

    @staticmethod
    async def on_shutdown(ctx):
        redis = ctx.get("redis")
        if redis:
            await redis.close()
