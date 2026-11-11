param([Parameter(Mandatory=$true)][string]$InstallDirectory)
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or -not $env:RUNNER_TEMP) { throw 'Disposable hosted runner required' }
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$probeDirectory=Join-Path $env:RUNNER_TEMP ('bs-native-probe-'+[guid]::NewGuid().ToString('N'))
$data=Join-Path $probeDirectory 'data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $data 'cli-initialized'),'1')
$env:SAG_DATA_DIR=$data
$env:SAG_DESKTOP_DATA_DIR=$data
$env:WEBVIEW2_USER_DATA_FOLDER=Join-Path $probeDirectory 'webview'
$listener=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$port=([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--remote-debugging-port=$port --remote-debugging-address=127.0.0.1"
$env:BS_NATIVE_DEBUG_PORT=$port
$policyKey='HKLM:\SOFTWARE\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments'
if ((Get-ItemProperty -Path $policyKey -Name 'sag-desktop.exe' -ErrorAction SilentlyContinue)) {
  throw 'Refusing to overwrite an existing desktop WebView2 policy'
}
New-Item -Path $policyKey -Force | Out-Null
New-ItemProperty -Path $policyKey -Name 'sag-desktop.exe' -Value "--remote-debugging-port=$port" -PropertyType String -Force | Out-Null
$desktop=Join-Path $InstallDirectory 'sag-desktop.exe'
$cli=Join-Path $InstallDirectory 'bin\sag.exe'
$process=$null
try {
  $process=Start-Process -FilePath $desktop -WorkingDirectory $InstallDirectory -PassThru
  $deadline=[DateTime]::UtcNow.AddSeconds(60)
  do {
    Start-Sleep -Milliseconds 500
    $process.Refresh()
    if ($process.HasExited) { throw "Desktop exited: $($process.ExitCode)" }
  } while ($process.MainWindowHandle -eq 0 -and [DateTime]::UtcNow -lt $deadline)
  if ($process.MainWindowHandle -eq 0) { throw 'No desktop window handle' }
  Start-Sleep -Seconds 5
  $root=[System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
  if (-not $root) { throw 'No UI Automation root' }
  $nodes=$root.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
  $items=@()
  foreach ($node in $nodes) {
    try { $info=$node.Current; if ($info.Name) { $items+=@{name=$info.Name;type=$info.ControlType.ProgrammaticName} } } catch {}
    if ($items.Count -ge 120) { break }
  }
  @{window_handle=$process.MainWindowHandle.ToInt64();node_count=$nodes.Count;items=$items} | ConvertTo-Json -Depth 6
  python tests/bs/native_probe_windows.py
  if ($LASTEXITCODE -ne 0) { throw 'Native WebView interaction failed' }
} finally {
  if ($process) { $process.Refresh(); if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force } }
  if (Test-Path -LiteralPath (Join-Path $data 'sag-service.json')) { & $cli service stop | Out-Null }
  Remove-ItemProperty -Path $policyKey -Name 'sag-desktop.exe' -ErrorAction SilentlyContinue
}
