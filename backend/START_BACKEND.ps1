$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $backend
try {
    if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
        throw "backend/.venv belum ada. Jalankan ..\SETUP_CLEAN_WINDOWS.ps1 terlebih dahulu."
    }
    & .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
} finally {
    Pop-Location
}
