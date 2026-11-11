param([Parameter(Mandatory=$true)][string]$InstallDirectory)

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted' -or -not $env:RUNNER_TEMP) {
  throw 'This test may only run on a disposable GitHub-hosted Windows runner.'
}

$desktop = Join-Path $InstallDirectory 'sag-desktop.exe'
$cli = Join-Path $InstallDirectory 'bin\sag.exe'
if (-not (Test-Path -LiteralPath $desktop) -or -not (Test-Path -LiteralPath $cli)) {
  throw 'The installed application and CLI are required.'
}

$probeDirectory = Join-Path $env:RUNNER_TEMP ('bs-native-ui-' + [guid]::NewGuid().ToString('N'))
$data = Join-Path $probeDirectory 'data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $data 'cli-initialized'), '1')
$env:SAG_DATA_DIR = $data
$env:SAG_DESKTOP_DATA_DIR = $data
$env:WEBVIEW2_USER_DATA_FOLDER = Join-Path $probeDirectory 'webview'
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()
$env:BS_NATIVE_DEBUG_PORT = $port

# Hosted runners run elevated. Newer WebView2 ignores user/environment debug
# overrides for elevated processes, so install only this app's temporary
# machine policy and remove it in finally. Refuse to overwrite existing policy.
$policyKey = 'HKLM:\SOFTWARE\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments'
if (Get-ItemProperty -Path $policyKey -Name 'sag-desktop.exe' -ErrorAction SilentlyContinue) {
  throw 'Refusing to overwrite an existing desktop WebView2 policy.'
}
$policyInstalled = $false
$process = $null
try {
  New-Item -Path $policyKey -Force | Out-Null
  New-ItemProperty -Path $policyKey -Name 'sag-desktop.exe' -Value "--remote-debugging-port=$port" -PropertyType String | Out-Null
  $policyInstalled = $true
  $process = Start-Process -FilePath $desktop -WorkingDirectory $InstallDirectory -PassThru
  $deadline = [DateTime]::UtcNow.AddSeconds(60)
  do {
    Start-Sleep -Milliseconds 500
    $process.Refresh()
    if ($process.HasExited) { throw "Desktop exited: $($process.ExitCode)" }
  } while ($process.MainWindowHandle -eq 0 -and [DateTime]::UtcNow -lt $deadline)
  if ($process.MainWindowHandle -eq 0) { throw 'No desktop window handle.' }
  python tests/bs/native_ui_windows.py
  if ($LASTEXITCODE -ne 0) { throw 'Native WebView interaction failed.' }
} finally {
  if ($process) { $process.Refresh(); if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force } }
  if (Test-Path -LiteralPath (Join-Path $data 'sag-service.json')) { & $cli service stop | Out-Null }
  if ($policyInstalled) { Remove-ItemProperty -Path $policyKey -Name 'sag-desktop.exe' -ErrorAction SilentlyContinue }
}
