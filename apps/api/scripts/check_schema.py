import asyncio

from src.database.neon_client import acquire


async def main() -> None:
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
        )
        for row in rows:
            print(row["column_name"])


if __name__ == "__main__":
    asyncio.run(main())
