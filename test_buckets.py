import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

env_path = Path(".env")
load_dotenv(env_path)

supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))

try:
    buckets = supabase.storage.list_buckets()
    print("Buckets:")
    for b in buckets:
        print(f" - {b.name} (public: {b.public})")
except Exception as e:
    print("Error:", str(e))
