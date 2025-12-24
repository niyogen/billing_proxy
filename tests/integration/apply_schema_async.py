import asyncio
import asyncpg
import os

async def main():
    print("Connecting to DB...")
    # Use environment variables or hardcoded test defaults
    # PGDATABASE is "litellm" in docker-compose.yml
    conn = await asyncpg.connect(
        host="db",
        user="litellm_user",
        password="test_password",
        database="litellm"
    )
    print("Connected. Applying schema...")
    with open("/app/db/schema.sql", "r") as f:
        schema = f.read()
    
    await conn.execute(schema)
    print("Schema applied successfully.")
    
    # Check
    val = await conn.fetchval("SELECT to_regclass('public.litellm_usage')")
    print(f"Table check: {val}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
