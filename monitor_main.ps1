# monitor_main.ps1

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = "python"   # or full path, e.g. C:\Users\Luiz\AppData\Local\Programs\Python\Python313\python.exe
$MainFile = Join-Path $ProjectDir "main.py"
$TargetHour = 6
$TargetMinute = 30
$CheckIntervalSeconds = 20
$LastRunDate = $null

Write-Host "Monitor started at $(Get-Date)"
Write-Host "Project dir: $ProjectDir"
Write-Host "Watching for daily execution at 06:30..."

while ($true) {
    $now = Get-Date

    $todayRunTime = Get-Date -Hour $TargetHour -Minute $TargetMinute -Second 0

    $shouldRunToday =
        ($now -ge $todayRunTime) -and
        ($LastRunDate -ne $now.Date)

    if ($shouldRunToday) {
        Write-Host ""
        Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Time reached. Starting main.py..."

        if (-not (Test-Path $MainFile)) {
            Write-Host "ERROR: main.py not found at $MainFile"
        }
        else {
            Push-Location $ProjectDir
            try {
                & $PythonExe $MainFile
                $exitCode = $LASTEXITCODE
                Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] main.py finished with exit code: $exitCode"
            }
            catch {
                Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Error while running main.py: $_"
            }
            finally {
                Pop-Location
            }
        }

        $LastRunDate = $now.Date
    }

    Start-Sleep -Seconds $CheckIntervalSeconds
}