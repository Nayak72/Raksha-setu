import httpx
url = "https://wcaggixrdosfkewalokc.supabase.co/storage/v1/object/public/Input%20Images/zone1/normal_img0042.jpg"
try:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url)
        print("Status Code:", resp.status_code)
        resp.raise_for_status()
        print("Success, downloaded", len(resp.content), "bytes")
except Exception as e:
    print("Error:", str(e))
