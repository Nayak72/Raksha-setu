import asyncio
import json
from app.db.supabase_client import get_supabase

async def check():
    sb = get_supabase()
    res = sb.table("agent_logs").select("*").execute()
    with open("agent_logs_out.json", "w", encoding="utf-8") as f:
        json.dump(res.data, f, ensure_ascii=False, indent=2)

asyncio.run(check())
