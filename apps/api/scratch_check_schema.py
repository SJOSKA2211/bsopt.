
import asyncio
from src.database.neon_client import acquire

async def check_schema():
    async with acquire() as conn:
        rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'feature_snapshots' ORDER BY ordinal_position")
        print("Columns in feature_snapshots:", [r['column_name'] for r in rows])

if __name__ == "__main__":
    asyncio.run(check_schema())
