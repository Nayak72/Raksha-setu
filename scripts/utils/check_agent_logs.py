import asyncio
import json
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from app.db.supabase_client import get_supabase

async def check():
    sb = get_supabase()
    res = sb.table("agent_logs").select("*").execute()
    log_path = os.path.join(project_root, "logs", "agent_logs_out.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(res.data, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved agent logs to {log_path}")

asyncio.run(check())
