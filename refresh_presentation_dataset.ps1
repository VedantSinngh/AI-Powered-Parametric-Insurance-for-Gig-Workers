$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"

function Wait-ForBackend {
	param(
		[string]$HealthUrl = "http://localhost:8000/health",
		[int]$TimeoutSeconds = 90
	)

	$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
	while ((Get-Date) -lt $deadline) {
		try {
			$response = Invoke-RestMethod -Method Get -Uri $HealthUrl -TimeoutSec 5
			if ($response.status -eq "healthy") {
				return
			}
		}
		catch {
			# Backend may still be starting up.
		}
		Start-Sleep -Seconds 2
	}

	throw "Backend did not become healthy within $TimeoutSeconds seconds."
}

Write-Host "[1/4] Rebuilding backend container..." -ForegroundColor Cyan
Set-Location $backend

docker compose up -d --build backend | Out-Null

Write-Host "[2/4] Waiting for backend health..." -ForegroundColor Cyan
Wait-ForBackend

Write-Host "[3/4] Seeding fresh presentation dataset..." -ForegroundColor Cyan
$seedOutput = docker compose exec -T backend python scripts/seed_presentation_demo.py
$seedOutput | Write-Host

Write-Host "[4/4] Running smoke check..." -ForegroundColor Cyan
Set-Location $root
./demo_runner.ps1
