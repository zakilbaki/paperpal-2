import asyncio
import sys, os

# Add project root to PYTHONPATH dynamically
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.app.db.mongo import ping

async def main():
    ok = await ping()
    print("Mongo connection:", ok)

if __name__ == "__main__":
    asyncio.run(main())
