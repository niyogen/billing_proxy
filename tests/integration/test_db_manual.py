import asyncio
import os
import asyncpg

async def main():
    host = os.environ.get("PGHOST", "db")
    user = os.environ.get("PGUSER", "litellm_user")
    password = os.environ.get("PGPASSWORD", "test_password")
    database = os.environ.get("PGDATABASE", "litellm")
    port = int(os.environ.get("PGPORT", "5432"))
    
    try:
        conn = await asyncpg.connect(
            host=host, port=port, user=user, password=password, database=database
        )
        rows = await conn.fetch("SELECT * FROM litellm_usage")
        print(f"Total rows: {len(rows)}")
        for row in rows:
            print(dict(row))
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
