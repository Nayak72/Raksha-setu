import os
import psycopg2
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

host = "aws-0-ap-northeast-1.pooler.supabase.com"
port = "6543"
user = "postgres.wcaggixrdosfkewalokc"
password = os.getenv("SUPABASE_DB_PASSWORD")
dbname = "postgres"

try:
    print(f"Connecting to {host}:{port}...")
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname
    )
    conn.autocommit = True
    cursor = conn.cursor()
    print("Connected successfully!")
    
    with open("migrations/001_initial.sql", "r", encoding="utf-8") as f:
        m1 = f.read()
    with open("migrations/002_agent_logs.sql", "r", encoding="utf-8") as f:
        m2 = f.read()
        
    print("Executing 001_initial.sql...")
    cursor.execute(m1)
    print("Executing 002_agent_logs.sql...")
    cursor.execute(m2)
    
    print("Migrations applied successfully!")
    
except Exception as e:
    print(f"Connection failed: {e}")
