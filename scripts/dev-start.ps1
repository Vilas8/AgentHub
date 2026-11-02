# AgentHub Local Development Startup Script (Windows PowerShell)
# Run from the agenthub/ root directory

Write-Host "=== AgentHub Dev Startup ===" -ForegroundColor Cyan

# Check prerequisites
function Check-Command($name) {
    if (!(Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Warning "$name not found in PATH"
        return $false
    }
    return $true
}

$ok = $true
$ok = (Check-Command "python") -and $ok
$ok = (Check-Command "node") -and $ok
$ok = (Check-Command "npm") -and $ok

if (!$ok) {
    Write-Error "Missing prerequisites. See docs/development/ENVIRONMENT.md"
    exit 1
}

# Check .env
if (!(Test-Path ".env")) {
    Write-Warning ".env not found. Copying from .env.example ..."
    Copy-Item ".env.example" ".env"
    Write-Warning "Please edit .env with your credentials before continuing."
    exit 1
}

# Start backend in new window
Write-Host "Starting backend API ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd apps/api; pip install -r requirements.txt -q; alembic upgrade head; uvicorn app.main:app --reload --port 8000"
)

# Start frontend in new window
Write-Host "Starting frontend ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd apps/web; npm install --silent; npm run dev"
)

Write-Host ""
Write-Host "AgentHub starting up:" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
