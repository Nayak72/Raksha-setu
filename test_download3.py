import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

env_path = Path(".env")
load_dotenv(env_path)

supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))

try:
    files = supabase.storage.from_("Input Images").list("zone1")
    for f in files:
        if f.get("id") is not None:
            print(f"File: {f.get('name')}")
            # Try to download the first one
            data = supabase.storage.from_("Input Images").download(f"zone1/{f.get('name')}")
            print(f"Success, downloaded {len(data)} bytes")
            break
except Exception as e:
    print("Error:", str(e))
