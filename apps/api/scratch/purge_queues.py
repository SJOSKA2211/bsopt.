import asyncio

from src.queue.rabbitmq_client import get_rabbitmq_channel


async def purge() -> None:
    channel = await get_rabbitmq_channel()
    q1 = await channel.declare_queue("bs.watchdog", durable=True)
    await q1.purge()
    q2 = await channel.declare_queue("bs.scrapers", durable=True)
    await q2.purge()
    print("Queues purged")


if __name__ == "__main__":
    asyncio.run(purge())
