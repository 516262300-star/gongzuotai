param(
    [ValidateSet("Install", "Uninstall", "Status", "Run")]
    [string]$Mode = "Install"
)

$ErrorActionPreference = "Stop"

$TaskName = "CodexWorkbenchApp"
$TaskDescription = "Start the Codex personal workbench web app at Windows logon."
$Port = 8787
$RepoRoot = Split-Path -Parent $PSScriptRoot
$AppScript = Join-Path $RepoRoot "tools\workbench_app.py"
$LogDir = Join-Path $RepoRoot "logs"
$StdoutLog = Join-Path $LogDir "workbench_app_stdout.log"
$StderrLog = Join-Path $LogDir "workbench_app_stderr.log"
$AutostartLog = Join-Path $LogDir "workbench_autostart.log"

function Get-WorkbenchListener {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Get-PythonExe {
    $python = Get-Command python -ErrorAction Stop
    return $python.Source
}

function Quote-Argument([string]$Value) {
    $quote = [string]([char]34)
    return $quote + $Value.Replace($quote, $quote + $quote) + $quote
}

function Write-AutostartLog([string]$Message) {
    Add-Content -LiteralPath $AutostartLog -Encoding utf8 -Value "[$(Get-Date -Format s)] $Message"
}

function Show-Status {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    $listener = Get-WorkbenchListener

    if ($task) {
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Host "Task: $($task.TaskName)"
        Write-Host "State: $($task.State)"
        Write-Host "Last run: $($info.LastRunTime)"
        Write-Host "Last result: $($info.LastTaskResult)"
        Write-Host "Next run: $($info.NextRunTime)"
    } else {
        Write-Host "Task: not installed"
    }

    if ($listener) {
        Write-Host "Port: 127.0.0.1:$Port listening, PID $($listener.OwningProcess)"
    } else {
        Write-Host "Port: 127.0.0.1:$Port not listening"
    }
}

function Install-Task {
    if (-not (Test-Path -LiteralPath $AppScript)) {
        throw "Workbench app script not found: $AppScript"
    }

    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    $scriptPath = $PSCommandPath
    $actionArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-WindowStyle", "Hidden",
        "-File", (Quote-Argument $scriptPath),
        "-Mode", "Run"
    ) -join " "

    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument $actionArgs `
        -WorkingDirectory $RepoRoot
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
    $settings = New-ScheduledTaskSettingsSet `
        -MultipleInstances IgnoreNew `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries
    $principal = New-ScheduledTaskPrincipal `
        -UserId $identity `
        -LogonType Interactive `
        -RunLevel Limited

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description $TaskDescription `
        -Force | Out-Null

    Write-Host "Installed scheduled task: $TaskName"

    if (-not (Get-WorkbenchListener)) {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "Started scheduled task now."
    } else {
        Write-Host "127.0.0.1:$Port is already listening; skipped duplicate start."
    }
}

function Uninstall-Task {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Host "Scheduled task does not exist: $TaskName"
        return
    }

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task: $TaskName"
}

function Run-Server {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    $listener = Get-WorkbenchListener
    if ($listener) {
        Write-AutostartLog "127.0.0.1:$Port already listening; skip duplicate start. PID $($listener.OwningProcess)"
        return
    }

    $pythonExe = Get-PythonExe
    Write-AutostartLog "Starting workbench app with $pythonExe"

    Set-Location -LiteralPath $RepoRoot
    & $pythonExe $AppScript 1>> $StdoutLog 2>> $StderrLog
}

switch ($Mode) {
    "Install" { Install-Task; Show-Status }
    "Uninstall" { Uninstall-Task; Show-Status }
    "Status" { Show-Status }
    "Run" { Run-Server }
}
