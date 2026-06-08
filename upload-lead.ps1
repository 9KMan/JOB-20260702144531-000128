# upload-lead.ps1 — Production lead uploader for Software Factory MinIO bridge
# Usage: .\upload-lead.ps1 <lead.json>
# Requires: mc.exe in C:\Users\mongk\bin\mc.exe

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$SourcePath
)

$MC = "C:\Users\mongk\bin\mc.exe"
$ALIAS = "factory"
$LEADS_BUCKET = "leads"
$LOG_DIR = "$env:USERPROFILE\.factory\upload-logs"
$MAX_RETRIES = 3
$RETRY_DELAY = 2

function log {
    param([string]$msg, [string]$level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$level] $msg"
    Write-Host $line
    $logFile = "$LOG_DIR\upload-$(Get-Date -Format 'yyyyMMdd').log"
    if (-not (Test-Path $LOG_DIR)) {
        New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
    }
    Add-Content -Path $logFile -Value $line
}

function error-exit {
    param([string]$msg)
    log -msg $msg -level "ERROR"
    exit 1
}

if (-not (Test-Path $SourcePath)) {
    error-exit "File not found: $SourcePath"
}

if (-not (Test-Path $MC)) {
    error-exit "mc.exe not found at $MC"
}

$filename = Split-Path $SourcePath -Leaf

try {
    $jsonContent = Get-Content $SourcePath -Raw -Encoding UTF8
    $lead = $jsonContent | ConvertFrom-Json
} catch {
    error-exit "Invalid JSON: $_"
}

$required = @("lead_id", "client", "budget", "source")
$missing = @()
foreach ($field in $required) {
    if (-not $lead.PSObject.Properties[$field]) {
        $missing += $field
    }
}
if ($missing.Count -gt 0) {
    error-exit "Missing required fields: $($missing -join ', ')"
}

$lead | Add-Member -NotePropertyName "uploaded_at" -NotePropertyValue (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ") -Force
$lead | Add-Member -NotePropertyName "origin_host" -NotePropertyValue $env:COMPUTERNAME -Force
$lead | Add-Member -NotePropertyName "uploader" -NotePropertyValue "upload-lead.ps1" -Force

$tempFile = "$env:TEMP\$($lead.lead_id)_enriched.json"
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($tempFile, ($lead | ConvertTo-Json -Depth 5), $utf8NoBom)

$destPath = "$ALIAS/$LEADS_BUCKET/$filename"
$success = $false

for ($i = 1; $i -le $MAX_RETRIES; $i++) {
    log "Upload attempt $i of $MAX_RETRIES : $filename"
    $r = & $MC cp $tempFile $destPath 2>&1
    if ($LASTEXITCODE -eq 0) {
        $success = $true
        log "Upload confirmed: $($lead.lead_id) | $($lead.client) | $$($($lead.budget))"
        break
    }
    log "Attempt $i failed: $r" -level "WARN"
    if ($i -lt $MAX_RETRIES) {
        Start-Sleep -Seconds $RETRY_DELAY
    }
}

if ($success) {
    Start-Sleep -Milliseconds 500
    $verify = & $MC ls -json "$destPath" 2>&1
    if ($LASTEXITCODE -eq 0) {
        log "Verified in MinIO: $($lead.lead_id)"
    } else {
        log "Upload succeeded but verification failed" -level "WARN"
    }
}

Remove-Item $tempFile -Force -ErrorAction SilentlyContinue

if (-not $success) {
    error-exit "Upload failed after $MAX_RETRIES attempts"
}

Write-Output "LEAD_UPLOADED=$($lead.lead_id)"
exit 0