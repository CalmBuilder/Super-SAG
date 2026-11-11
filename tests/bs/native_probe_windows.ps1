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
} finally {
  if ($process) { $process.Refresh(); if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force } }
  if (Test-Path -LiteralPath (Join-Path $data 'sag-service.json')) { & $cli service stop | Out-Null }
}
