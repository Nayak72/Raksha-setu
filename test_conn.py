import asyncio
import asyncpg
import os
import ssl
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

async def test():
    host = os.getenv("SUPABASE_DB_HOST", "localhost").strip()
    port = os.getenv("SUPABASE_DB_PORT", "5432").strip()
    user = os.getenv("SUPABASE_DB_USER", "postgres").strip()
    password = os.getenv("SUPABASE_DB_PASSWORD", "").strip()
    dbname = os.getenv("SUPABASE_DB_NAME", "postgres").strip()
    
    print(f"Connecting to {host}:{port} as {user} (db: {dbname})")
    
    dsn = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    print(f"DSN: {dsn}")
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        conn = await asyncpg.connect(dsn, statement_cache_size=0, ssl=ssl_context)
        print("Connection successful!")
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(test())
