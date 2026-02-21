"""
FiscalSpy — Scheduler
Enqueues periodic jobs into the ARQ worker pool.
"""

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.models import CNPJMonitor
from app.workers.main import redis_settings_from_url

log = logging.getLogger(__name__)


async def get_arq_pool():
    from arq import create_pool
    return await create_pool(redis_settings_from_url(settings.redis_url))


# ── Jobs ──────────────────────────────────────────────
async def enqueue_all_monitors():
    """Every 30 min: enqueue a sync job for every active monitor."""
    pool = await get_arq_pool()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CNPJMonitor).where(CNPJMonitor.is_active == True)
        )
        monitors = result.scalars().all()

    log.info("Enqueueing sync for %d monitors", len(monitors))
    for m in monitors:
        await pool.enqueue_job("sync_cnpj", str(m.id))

    await pool.aclose()


async def enqueue_webhook_delivery():
    """Every 1 min: flush pending webhook deliveries."""
    pool = await get_arq_pool()
    await pool.enqueue_job("deliver_pending_webhooks")
    await pool.aclose()


# ── Main ──────────────────────────────────────────────
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        enqueue_all_monitors,
        trigger=IntervalTrigger(minutes=30),
        id="sync_monitors",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )

    scheduler.add_job(
        enqueue_webhook_delivery,
        trigger=IntervalTrigger(minutes=1),
        id="deliver_webhooks",
        replace_existing=True,
    )

    scheduler.start()
    log.info("Scheduler started")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        log.info("Scheduler stopped")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
