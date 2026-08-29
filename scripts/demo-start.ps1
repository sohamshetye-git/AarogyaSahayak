param(
    [string]$Action = "status"
)

# Root directory helper
$RootDir = Resolve-Path ".."
if ($Action -eq "start") {
    Write-Host "=================================================="
    Write-Host "  Aarogya Sahayak - Pinned Local Docker Startup"
    Write-Host "=================================================="
    
    # 1. Verify Docker daemon is responsive
    docker info > $null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker daemon is not running. Please start Docker."
        exit 1
    }

    # 2. Spin up pinned services
    docker compose up -d postgres milvus-standalone etcd minio neo4j n8n
    Write-Host "Docker containers launched. Awaiting service health..."
    Start-Sleep -Seconds 10

    # 3. Apply DB schemas & seed fixtures
    Write-Host "Applying database migrations and seeding demo accounts..."
    $env:APP_ENV="demo"
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
elseif ($Action -eq "stop") {
    Write-Host "Stopping all local Aarogya Sahayak containers..."
    docker compose down
}
elseif ($Action -eq "reset") {
    if ($env:APP_ENV -ne "demo") {
        Write-Error "Safety Rule Triggered: Resets only permitted under APP_ENV=demo"
        exit 1
    }
    Write-Host "Resetting local demo database state..."
    python -c "from app.database import Base, engine; Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)"
    python -m app.seeds.seed_data
    Write-Host "Database reset complete."
}
else {
    # Run Platform Diagnostics
    Write-Host "=================================================="
    Write-Host "  Aarogya Sahayak - Diagnostic Runbook Check"
    Write-Host "=================================================="
    docker compose ps
    python -m app.integrations.verify_all
}
