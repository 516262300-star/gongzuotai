param(
    [ValidateSet("Install", "Uninstall", "Status", "Ensure", "Run")]
    [string]$Mode = "Install"
)

$ErrorActionPreference = "Stop"

$TaskName = "CodexWorkbenchApp"
$TaskDescription = "Keep the Codex personal workbench web app running for the current user."
$Port = 8787
$RepoRoot = Split-Path -Parent $PSScriptRoot
$AppScript = Join-Path $RepoRoot "tools\workbench_app.py"
$HiddenLauncherScript = Join-Path $RepoRoot "tools\workbench_autostart.vbs"
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
    if (-not (Test-Path -LiteralPath $HiddenLauncherScript)) {
        throw "Hidden launcher script not found: $HiddenLauncherScript"
    }

    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    $actionArgs = @(
        "//B",
        "//Nologo",
        (Quote-Argument $HiddenLauncherScript),
        "Ensure"
    ) -join " "

    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $action = New-ScheduledTaskAction `
        -Execute "wscript.exe" `
        -Argument $actionArgs `
        -WorkingDirectory $RepoRoot
    $logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
    $watchdogTrigger = New-ScheduledTaskTrigger `
        -Once `
        -At (Get-Date).Date `
        -RepetitionInterval (New-TimeSpan -Minutes 5) `
        -RepetitionDuration (New-TimeSpan -Days 3650)
    $settings = New-ScheduledTaskSettingsSet `
        -MultipleInstances IgnoreNew `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries
    $principal = New-ScheduledTaskPrincipal `
        -UserId $identity `
        -LogonType Interactive `
        -RunLevel Limited

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger @($logonTrigger, $watchdogTrigger) `
        -Settings $settings `
        -Principal $principal `
        -Description $TaskDescription `
        -Force | Out-Null

    Write-Host "Installed scheduled task: $TaskName"

    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Started scheduled task now."
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

function Ensure-Server {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    $listener = Get-WorkbenchListener
    if ($listener) {
        Write-AutostartLog "127.0.0.1:$Port already listening; PID $($listener.OwningProcess)"
        return
    }

    $pythonExe = Get-PythonExe
    Write-AutostartLog "127.0.0.1:$Port not listening; starting workbench app with $pythonExe"
    $process = Start-Process `
        -FilePath $pythonExe `
        -ArgumentList @($AppScript) `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -PassThru

    Start-Sleep -Seconds 2
    $listener = Get-WorkbenchListener
    if ($listener) {
        Write-AutostartLog "Started workbench app. PID $($listener.OwningProcess)"
        return
    }

    if ($process.HasExited) {
        throw "Workbench app exited immediately with code $($process.ExitCode). See $StderrLog"
    }
    throw "Workbench app process started as PID $($process.Id), but 127.0.0.1:$Port is not listening yet."
}

switch ($Mode) {
    "Install" { Install-Task; Show-Status }
    "Uninstall" { Uninstall-Task; Show-Status }
    "Status" { Show-Status }
    "Ensure" { Ensure-Server }
    "Run" { Run-Server }
}
