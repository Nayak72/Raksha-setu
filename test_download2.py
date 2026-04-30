import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

env_path = Path(".env")
load_dotenv(env_path)

supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY"))

try:
    file_path = "zone1/normal_img0042.jpg"
    data = supabase.storage.from_("Input Images").download(file_path)
    print(f"Success, downloaded {len(data)} bytes")
except Exception as e:
    print("Error:", str(e))
