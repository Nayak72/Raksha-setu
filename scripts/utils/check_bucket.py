"""Check Supabase storage bucket contents."""
from supabase import create_client

sb = create_client(
    'https://wcaggixrdosfkewalokc.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndjYWdnaXhyZG9zZmtld2Fsb2tjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NzEzNzM0MywiZXhwIjoyMDkyNzEzMzQzfQ.eJZcUny9cXGNx0IDY24q9zo0qGhUwrmwnTWm356VsBQ'
)

bucket_name = "Input Images"
root = sb.storage.from_(bucket_name).list("")
print(f"=== Bucket: {bucket_name} ===")
print(f"Root items: {len(root)}")
print()

for item in root:
    name = item.get("name", "")
    item_id = item.get("id")
    if item_id is None:
        # It's a folder
        print(f"FOLDER: {name}/")
        try:
            contents = sb.storage.from_(bucket_name).list(name)
            for f in contents:
                fname = f.get("name", "")
                meta = f.get("metadata", {})
                size = meta.get("size", "?") if meta else "?"
                mimetype = meta.get("mimetype", "?") if meta else "?"
                fid = f.get("id")
                if fid is None:
                    # Sub-folder
                    print(f"  SUBFOLDER: {name}/{fname}/")
                    try:
                        sub_contents = sb.storage.from_(bucket_name).list(f"{name}/{fname}")
                        for sf in sub_contents:
                            sfname = sf.get("name", "")
                            smeta = sf.get("metadata", {})
                            ssize = smeta.get("size", "?") if smeta else "?"
                            smime = smeta.get("mimetype", "?") if smeta else "?"
                            print(f"    FILE: {sfname} (size={ssize}, type={smime})")
                    except Exception as e:
                        print(f"    ERROR: {e}")
                else:
                    print(f"  FILE: {fname} (size={size}, type={mimetype})")
        except Exception as e:
            print(f"  ERROR listing: {e}")
    else:
        meta = item.get("metadata", {})
        size = meta.get("size", "?") if meta else "?"
        print(f"FILE: {name} (size={size})")

print()
print("=== Public URLs ===")
for item in root:
    name = item.get("name", "")
    if item.get("id") is None:
        url = sb.storage.from_(bucket_name).get_public_url(name)
        print(f"{name}: {url}")
