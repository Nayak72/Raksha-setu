"""Quick DB diagnostic script."""
import asyncio
from app.db.supabase_client import get_pg_pool

async def check():
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Check if trigger exists
        rows = await conn.fetch(
            "SELECT trigger_name, event_manipulation, action_statement "
            "FROM information_schema.triggers "
            "WHERE event_object_table = 'detections'"
        )
        if rows:
            for r in rows:
                print(f"Trigger: {r['trigger_name']} ON {r['event_manipulation']}")
                print(f"  Action: {r['action_statement']}")
        else:
            print("NO TRIGGERS found on detections table!")

        # Check if the notify function exists
        funcs = await conn.fetch(
            "SELECT proname FROM pg_proc WHERE proname LIKE '%detect%' OR proname LIKE '%notify%'"
        )
        print(f"\nRelevant functions: {[r['proname'] for r in funcs]}")

        # Test manual NOTIFY
        await conn.execute("NOTIFY new_detection, '{\"zone_id\": \"test123\"}'")
        print("\nManual NOTIFY sent OK")

    await pool.close()

asyncio.run(check())
