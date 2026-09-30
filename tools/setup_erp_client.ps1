param([Parameter(Mandatory=$true)][string]$ClientExe)
$ErrorActionPreference = 'Stop'
$clientPath = (Resolve-Path -LiteralPath $ClientExe).Path
if ([IO.Path]::GetExtension($clientPath) -ne '.exe') { throw '请选择 LeedisClient.exe' }
$chromePath = Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'
if (-not (Test-Path -LiteralPath $chromePath)) { throw '未找到 Google Chrome' }
$configDir = Join-Path $env:LOCALAPPDATA 'LeedisDesktop'
New-Item -ItemType Directory -Path $configDir -Force | Out-Null
$configPath = Join-Path $configDir 'workbench-config.json'
if (Test-Path -LiteralPath $configPath) {
    Copy-Item -LiteralPath $configPath -Destination ($configPath + '.' + (Get-Date -Format yyyyMMddHHmmss) + '.bak')
}
@{client_exe=$clientPath} | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding utf8
# Leedis workbench_bridge.py resolves this exact compatibility shortcut.
$compatDesktop = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Desktop'
New-Item -ItemType Directory -Path $compatDesktop -Force | Out-Null
$shortcutPath = Join-Path $compatDesktop 'ERP Chrome.lnk'
if (Test-Path -LiteralPath $shortcutPath) {
    Copy-Item -LiteralPath $shortcutPath -Destination ($shortcutPath + '.' + (Get-Date -Format yyyyMMddHHmmss) + '.bak')
}
$shellObject = New-Object -ComObject WScript.Shell
$shortcut = $shellObject.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $chromePath
$profilePath = Join-Path $configDir 'erp-chrome'
$shortcut.Arguments = '--remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir="' + $profilePath + '" --no-first-run --no-default-browser-check'
$shortcut.Description = 'Leedis 客户端专用 ERP 浏览器'
$shortcut.Save()
Write-Host '已配置 Leedis 客户端与专用 ERP Chrome。请在客户端登录后运行工作台任务。'
