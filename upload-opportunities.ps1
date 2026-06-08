# upload-opportunities.ps1 - Transform Gig Pipeline opportunities to leads and upload to MinIO
param(
    [string]$WatchFolder = "D:\clawd\gig-pipeline\stage1-opportunities",
    [string]$MC = "C:\Users\mongk\bin\mc.exe",
    [string]$MinioAlias = "factory",
    [switch]$Verbose
)

function Parse-Rate {
    param([string]$Rate)
    if ($null -eq $Rate -or $Rate -eq "") { return @{estimated = $null; raw = $null} }
    if ($Rate -match '\$(\d+)-?(\d+)?\s*/\s*hr') {
        $lo = [int]$Matches[1]; $hi = if ($Matches[2]) { [int]$Matches[2] } else { $lo }
        return @{estimated = [Math]::Max($lo, 45); raw = "$lo-$hi/hr"; hourly = $true }
    }
    if ($Rate -match '\$(\d+)\s*/\s*hr') {
        return @{estimated = [int]$Matches[1]; raw = "$($Matches[1])/hr"; hourly = $true }
    }
    if ($Rate -match '\$(\d+)-?(\d+)?\s*/\s*(project|gig|month)') {
        $lo = [int]$Matches[1]; $hi = if ($Matches[2]) { [int]$Matches[2] } else { $lo }
        return @{estimated = [Math]::Max([int]($lo / 160), 30); raw = $Rate; hourly = $false}
    }
    if ($Rate -match 'competitive|Series') {
        return @{estimated = 65; raw = "competitive"; hourly = $true}
    }
    return @{estimated = $null; raw = $Rate; hourly = $null}
}

function New-LeadId {
    param([string]$Platform, [string]$OpId)
    $slug = "$Platform-$OpId".ToLower() -replace '[^a-z0-9\-]', ''
    $ts = (Get-Date).ToString("yyyyMMdd")
    return "UP-$ts-$slug"
}

function ConvertTo-Lead {
    param($Opp, [string]$Generated)
    $rateInfo = Parse-Rate $Opp.rate
    $budget = if ($rateInfo.hourly) {
        if ($rateInfo.estimated) { $rateInfo.estimated * 10 } else { 500 }
    } else {
        if ($rateInfo.raw -match '\$(\d+)') { [int]$Matches[1] } else { 500 }
    }
    $techStack = if ($Opp.skillsMatch) { $Opp.skillsMatch } else { @() }
    $description = if ($Opp.notes) { $Opp.notes } else { "$($Opp.title) at $($Opp.company) via $($Opp.platform)" }
    $timeline = switch -Regex ($Opp.platform) {
        "RemoteOK|Lateral" { "full-time" }
        "Fiverr" { "fixed-gig" }
        default { "flexible" }
    }
    return @{
        lead_id       = New-LeadId $Opp.platform $Opp.id
        client        = if ($Opp.company) { $Opp.company } else { $Opp.platform }
        title         = $Opp.title
        budget        = $budget
        rate          = $rateInfo.raw
        source        = "$($Opp.platform.ToLower())-gig-pipeline"
        url           = $Opp.url
        timeline      = $timeline
        tech_stack    = $techStack
        description   = $description
        uploaded_at   = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
        origin_host   = "kainui-gig-pipeline"
        uploader      = "gig-pipeline-stage1"
        generated_at  = $Generated
    }
}

# Main: find the LATEST .json file in watch folder
Write-Host "Scanning: $WatchFolder"
if (-not (Test-Path $WatchFolder)) {
    Write-Host "[ERROR] Folder not found: $WatchFolder"; exit 1
}

$latestJson = Get-ChildItem $WatchFolder -Filter "*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latestJson) {
    Write-Host "[WARN] No JSON files found in $WatchFolder"; exit 0
}

Write-Host "Processing: $($latestJson.Name) ($([Math]::Round($latestJson.Length/1KB,1)) KB)"

$content = Get-Content $latestJson.FullName -Raw -Encoding UTF8
$stage1 = $content | ConvertFrom-Json

$opportunities = $stage1.opportunities
if (-not $opportunities -or $opportunities.Count -eq 0) {
    Write-Host "[WARN] No opportunities in $($latestJson.Name)"; exit 0
}

$generated = $stage1.generated
Write-Host "Found $($opportunities.Count) opportunities, uploading..."

$uploadDir = "D:\clawd\gig-pipeline\uploaded"
if (-not (Test-Path $uploadDir)) {
    New-Item -ItemType Directory -Path $uploadDir -Force | Out-Null
}

$uploaded = 0; $skipped = 0
foreach ($opp in $opportunities) {
    $lead = ConvertTo-Lead $opp $generated
    $leadFile = Join-Path $uploadDir "$($lead.lead_id).json"
    $jsonOut = $lead | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($leadFile, $jsonOut, (New-Object System.Text.UTF8Encoding $false))

    # Upload to MinIO incoming/ folder (poll-leads watches this)
    $target = "$MinioAlias/leads/incoming/$($lead.lead_id).json"
    $result = & $MC cp $leadFile $target 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  UP: $($lead.lead_id) | $($lead.client) | `$$($lead.budget) | $($lead.rate)"
        if ($Verbose) { Write-Host "     URL: $($lead.url)" }
        $uploaded++
    } else {
        Write-Host "  FAIL: $($lead.lead_id) - $result"
        $skipped++
    }
}

Write-Host ""
Write-Host "Done: $uploaded uploaded, $skipped failed"
Write-Host "Lead files saved to: $uploadDir"

# Mark source as processed
$processed = Join-Path $WatchFolder "processed"
if (-not (Test-Path $processed)) {
    New-Item -ItemType Directory -Path $processed -Force | Out-Null
}
Move-Item $latestJson.FullName (Join-Path $processed $latestJson.Name) -Force

exit [int]($skipped -gt 0)
