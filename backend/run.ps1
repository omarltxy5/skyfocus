# Run SkyFocus API from the correct directory (backend root).
Set-Location $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\uvicorn.exe" app.main:app --reload --host 127.0.0.1 --port 8000
