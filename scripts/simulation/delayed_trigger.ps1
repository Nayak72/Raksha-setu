Start-Sleep -Seconds 10
Invoke-RestMethod -Uri http://localhost:8001/api/v1/detect `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"zone_id": "cc0a2353-6648-406d-a8e2-32e792bb5de0", "count": 99, "metadata": {"source": "drone_camera"}}'
