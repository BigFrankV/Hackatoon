$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$environmentFiles = @(
    @{ Example = ".env.example"; Local = ".env" },
    @{ Example = "backend/.env.example"; Local = "backend/.env" },
    @{ Example = "frontend/.env.example"; Local = "frontend/.env" }
)

foreach ($file in $environmentFiles) {
    if (-not (Test-Path $file.Local)) {
        Copy-Item $file.Example $file.Local
        Write-Host "Created $($file.Local) from $($file.Example)"
    }
}

function Get-DotEnvValue {
    param(
        [string]$Path,
        [string]$Name
    )

    foreach ($line in Get-Content $Path) {
        if ($line -match "^\s*$([regex]::Escape($Name))\s*=\s*(.*)$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }

    return ""
}

function Set-DotEnvValue {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value
    )

    $lines = [System.Collections.Generic.List[string]]::new()
    if (Test-Path $Path) {
        foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
            [void]$lines.Add($line)
        }
    }

    $pattern = "^\s*$([regex]::Escape($Name))\s*="
    $updated = $false
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match $pattern) {
            $lines[$index] = "$Name=$Value"
            $updated = $true
            break
        }
    }
    if (-not $updated) {
        [void]$lines.Add("$Name=$Value")
    }

    [System.IO.File]::WriteAllText(
        $Path,
        (($lines -join "`n") + "`n"),
        (New-Object System.Text.UTF8Encoding($false))
    )
}

function New-LocalPassword {
    $bytes = New-Object byte[] 32
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    } finally {
        $generator.Dispose()
    }
    return [System.BitConverter]::ToString($bytes).Replace("-", "").ToLowerInvariant()
}

$demoPasswordKeys = @(
    "DEV_SEED_NORTH_ADMIN_PASSWORD",
    "DEV_SEED_NORTH_USER_PASSWORD",
    "DEV_SEED_SOUTH_ADMIN_PASSWORD",
    "DEV_SEED_SOUTH_USER_PASSWORD"
)
foreach ($key in $demoPasswordKeys) {
    $password = Get-DotEnvValue -Path ".env" -Name $key
    if ([string]::IsNullOrWhiteSpace($password)) {
        $password = New-LocalPassword
        Set-DotEnvValue -Path ".env" -Name $key -Value $password
    } elseif ($password.Length -lt 12) {
        throw "$key must contain at least 12 characters in .env."
    }
}

$adminEmail = Get-DotEnvValue -Path ".env" -Name "BOOTSTRAP_SUPERADMIN_EMAIL"
$adminPassword = Get-DotEnvValue -Path ".env" -Name "BOOTSTRAP_SUPERADMIN_PASSWORD"
$databaseName = Get-DotEnvValue -Path ".env" -Name "POSTGRES_DB"
$databaseUser = Get-DotEnvValue -Path ".env" -Name "POSTGRES_USER"

if ([string]::IsNullOrWhiteSpace($databaseName)) {
    $databaseName = "licitaciones"
}
if ([string]::IsNullOrWhiteSpace($databaseUser)) {
    $databaseUser = "licitaciones"
}

if ([string]::IsNullOrWhiteSpace($adminEmail) -or $adminEmail -notmatch "^[^@\s]+@[^@\s]+\.[^@\s]+$") {
    throw "Set BOOTSTRAP_SUPERADMIN_EMAIL to a valid address in .env, then run this script again."
}
if ([string]::IsNullOrWhiteSpace($adminPassword) -or $adminPassword.Length -lt 12) {
    throw "Set BOOTSTRAP_SUPERADMIN_PASSWORD to at least 12 characters in .env, then run this script again."
}

$pgadminDirectory = Join-Path $repoRoot "pgadmin"
$serverTemplatePath = Join-Path $pgadminDirectory "servers.json.example"
$serverConfigPath = Join-Path $pgadminDirectory "servers.json"
$serverConfig = [System.IO.File]::ReadAllText($serverTemplatePath)
$serverConfig = $serverConfig.Replace('${POSTGRES_DB}', $databaseName).Replace('${POSTGRES_USER}', $databaseUser)
[System.IO.File]::WriteAllText($serverConfigPath, $serverConfig, (New-Object System.Text.UTF8Encoding($false)))

$frontendAnswer = Read-Host "Iniciar frontend en Docker? (s/N)"
$startFrontendInDocker = $frontendAnswer -match "^(s|si|y|yes)$"
$composeProfiles = @("--profile", "dev", "--profile", "jobs")
if ($startFrontendInDocker) {
    $composeProfiles += @("--profile", "frontend")
}

docker compose @composeProfiles config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose configuration is invalid."
}

docker compose @composeProfiles up --build --detach
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed to start. Review the error above."
}

$backendContainerId = docker compose --profile dev ps --quiet backend
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($backendContainerId)) {
    throw "The backend container was not created."
}
$pgadminContainerId = docker compose --profile dev ps --quiet pgadmin
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($pgadminContainerId)) {
    throw "The pgAdmin container was not created."
}

$ready = $false
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    $backendHealth = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $backendContainerId
    $pgadminHealth = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $pgadminContainerId
    if ($LASTEXITCODE -eq 0 -and $backendHealth.Trim() -eq "healthy" -and $pgadminHealth.Trim() -eq "healthy") {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    throw "The backend and pgAdmin did not both become healthy. Run 'docker compose --profile dev logs backend pgadmin' to inspect startup."
}

Write-Host ""
Write-Host "Development environment is ready:"
if ($startFrontendInDocker) {
    Write-Host "  Frontend (Docker): http://localhost:5173"
} else {
    Write-Host "  Frontend not started in Docker. Run 'npm run dev' from frontend/ for hot reload."
}
Write-Host "  API docs: http://localhost:8000/docs"
Write-Host "  Document worker: started for PDF/DOCX processing"
Write-Host "  pgAdmin:  http://localhost:5050 (database server preconfigured)"
Write-Host "  Database: localhost:5432"
Write-Host ""
Write-Host "Stop services with: docker compose --profile dev --profile frontend down"
