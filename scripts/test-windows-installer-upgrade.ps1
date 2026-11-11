# Isolated test of the actual NSIS package, using only the installation created
# by smoke-windows.ps1 on a disposable GitHub-hosted Windows runner.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Installer,
    [Parameter(Mandatory = $true)][string]$SmokeDirectory
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT' -or $env:GITHUB_ACTIONS -ne 'true' -or
    $env:RUNNER_ENVIRONMENT -ne 'github-hosted' -or -not $env:RUNNER_TEMP) {
    throw 'This test is restricted to an explicitly selected disposable GitHub-hosted Windows runner.'
}
$runnerRoot = [IO.Path]::GetFullPath($env:RUNNER_TEMP).TrimEnd('\') + '\'
$smoke = (Resolve-Path -LiteralPath $SmokeDirectory).Path
if (-not $smoke.StartsWith($runnerRoot, [StringComparison]::OrdinalIgnoreCase) -or
    -not (Split-Path -Leaf $smoke).StartsWith('sag-windows-smoke-')) {
    throw 'The smoke installation is not in the expected disposable runner directory.'
}
$setup = (Resolve-Path -LiteralPath $Installer).Path
$installDir = Join-Path $smoke 'installation'
$desktop = Join-Path $installDir 'sag-desktop.exe'
$cli = Join-Path $installDir 'bin\sag.exe'
$uninstall = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\SAG Wiki'
$registration = Get-ItemProperty -LiteralPath $uninstall
if ($registration.DisplayName -ne 'Super-SAG' -or $registration.DisplayVersion -ne '0.1.0') {
    throw 'The disposable smoke installation has an unexpected identity.'
}
$publisher = [string]$registration.Publisher
$product = if ($publisher) { "HKCU:\Software\$publisher\SAG Wiki" } else { 'HKCU:\Software\SAG Wiki' }
$productItem = Get-Item -LiteralPath $product
$registeredDir = [string]$productItem.GetValue('')
if ([IO.Path]::GetFullPath($registeredDir).TrimEnd('\') -ne [IO.Path]::GetFullPath($installDir).TrimEnd('\')) {
    throw 'The registered directory does not belong to the disposable smoke run.'
}
foreach ($path in @($desktop, $cli)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing smoke binary: $path" }
}
$fixture = Join-Path $smoke 'installer-upgrade-fixtures'
New-Item -ItemType Directory -Path $fixture -Force | Out-Null
$backup = Join-Path $fixture 'original-sag.exe'
Copy-Item -LiteralPath $cli -Destination $backup
$dataMarker = Join-Path $smoke 'data\upgrade-marker.txt'
[IO.File]::WriteAllText($dataMarker, 'test data preserved')
$desktopHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $desktop).Hash
$originalVersion = $registration.DisplayVersion
$oldTestMode = [Environment]::GetEnvironmentVariable('SUPER_SAG_INSTALLER_TEST_MODE', 'Process')
$oldDataDir = [Environment]::GetEnvironmentVariable('SAG_DATA_DIR', 'Process')
$oldDesktopDataDir = [Environment]::GetEnvironmentVariable('SAG_DESKTOP_DATA_DIR', 'Process')
$env:SAG_DATA_DIR = Join-Path $smoke 'data'
$env:SAG_DESKTOP_DATA_DIR = Join-Path $smoke 'data'
$checks = [Collections.Generic.List[string]]::new()
$cleanupError = $null

function Invoke-Setup([string]$Destination) {
    $process = Start-Process -FilePath $setup -ArgumentList "/S /NS /D=$Destination" -PassThru
    if (-not $process.WaitForExit(120000)) { $process.Kill(); throw 'Installer timed out.' }
    return $process.ExitCode
}
function Assert-Preserved([string]$BeforeCliHash) {
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $desktop).Hash -ne $desktopHash -or
        (Get-FileHash -Algorithm SHA256 -LiteralPath $cli).Hash -ne $BeforeCliHash -or
        [IO.File]::ReadAllText($dataMarker) -ne 'test data preserved') {
        throw 'A refused installation changed a managed binary or the data marker.'
    }
}
function Reject-Version([string]$Name, [string]$Version, [string]$Destination = $installDir) {
    Set-ItemProperty -LiteralPath $uninstall -Name 'DisplayVersion' -Value $Version
    $before = (Get-FileHash -Algorithm SHA256 -LiteralPath $cli).Hash
    if ((Invoke-Setup $Destination) -eq 0) { throw "$Name should have been refused." }
    Assert-Preserved $before
    if ((Get-ItemPropertyValue -LiteralPath $uninstall -Name 'DisplayVersion') -ne $Version) {
        throw "$Name changed the registered version."
    }
    $checks.Add($Name)
}
try {
    Reject-Version 'unknown newer version refused' '99.0.0'
    Reject-Version 'invalid registered version refused' 'not-a-version'
    Reject-Version 'unidentified same-version silent reinstall refused' '0.1.0'
    Remove-ItemProperty -LiteralPath $uninstall -Name 'DisplayVersion'
    $before = (Get-FileHash -Algorithm SHA256 -LiteralPath $cli).Hash
    if ((Invoke-Setup $installDir) -eq 0) { throw 'A missing registered version should have been refused.' }
    Assert-Preserved $before
    if ((Get-ItemProperty -LiteralPath $uninstall).PSObject.Properties['DisplayVersion']) {
        throw 'Refused installation recreated the missing version.'
    }
    $checks.Add('missing version refused')

    # Remove only this runner's two freshly created keys to emulate a damaged
    # installation with binaries left on disk. Restore the exact exports even
    # when the test fails.
    Set-ItemProperty -LiteralPath $uninstall -Name 'DisplayVersion' -Value $originalVersion
    $uninstallNative = 'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\SAG Wiki'
    $productNative = if ($publisher) { "HKCU\Software\$publisher\SAG Wiki" } else { 'HKCU\Software\SAG Wiki' }
    $uninstallExport = Join-Path $fixture 'uninstall.reg'
    $productExport = Join-Path $fixture 'product.reg'
    & reg.exe export $uninstallNative $uninstallExport /y | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cannot back up the disposable uninstall key.' }
    & reg.exe export $productNative $productExport /y | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cannot back up the disposable product key.' }
    try {
        Remove-Item -LiteralPath $uninstall -Recurse -Force
        Remove-Item -LiteralPath $product -Recurse -Force
        $before = (Get-FileHash -Algorithm SHA256 -LiteralPath $cli).Hash
        if ((Invoke-Setup $installDir) -eq 0) { throw 'Unregistered existing binaries should have been refused.' }
        Assert-Preserved $before
        if ((Test-Path -LiteralPath $uninstall) -or (Test-Path -LiteralPath $product)) {
            throw 'The refused orphan installation recreated registry entries.'
        }
        $checks.Add('unregistered existing installation refused')
    } finally {
        & reg.exe import $productExport | Out-Null
        $productRestoreStatus = $LASTEXITCODE
        & reg.exe import $uninstallExport | Out-Null
        $uninstallRestoreStatus = $LASTEXITCODE
        if ($productRestoreStatus -ne 0 -or $uninstallRestoreStatus -ne 0) {
            throw 'Cannot restore the disposable test registration.'
        }
    }

    $rustSource = Join-Path $fixture 'fake-sag.rs'
    $fake = Join-Path $fixture 'fake-sag.exe'
    @'
use std::{env, thread, time::Duration};
fn main() {
    match env::var("SUPER_SAG_INSTALLER_TEST_MODE").unwrap_or_default().as_str() {
        "known" => print!("{}", r#"{"version":"0.2.9","build_id":"release-d0ef53a3834270d4","channel":"release","protocol_version":2}"#),
        "protocol20" => print!("{}", r#"{"version":"0.2.9","build_id":"release-d0ef53a3834270d4","channel":"release","protocol_version":20}"#),
        "timeout" => thread::sleep(Duration::from_secs(8)),
        "error" => std::process::exit(7),
        _ => print!("{}", r#"{"version":"0.2.9","build_id":"release-unknown","channel":"release","protocol_version":2}"#),
    }
}
'@ | Set-Content -LiteralPath $rustSource -Encoding utf8
    & rustc --edition=2021 $rustSource -o $fake
    if ($LASTEXITCODE -ne 0) { throw 'Cannot build the isolated CLI identity fixture.' }
    Copy-Item -LiteralPath $fake -Destination $cli -Force
    foreach ($mode in @('unknown', 'protocol20', 'error', 'timeout')) {
        $env:SUPER_SAG_INSTALLER_TEST_MODE = $mode
        Reject-Version "unrecognized or failing old CLI ($mode) refused" '0.2.9'
        if ($mode -eq 'timeout') { Start-Sleep -Seconds 4 }
    }
    $env:SUPER_SAG_INSTALLER_TEST_MODE = 'known'
    $originalUninstallCommand = [string](Get-ItemPropertyValue -LiteralPath $uninstall -Name 'UninstallString')
    try {
        Remove-ItemProperty -LiteralPath $uninstall -Name 'UninstallString'
        Reject-Version 'known identity with incomplete registration refused' '0.2.9'
    } finally {
        Set-ItemProperty -LiteralPath $uninstall -Name 'UninstallString' -Value $originalUninstallCommand
    }
    # The NSIS installer must not silently replace a matching MSI even when
    # its registered uninstall command uses an absolute msiexec path.
    $userMsi = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\SuperSAG-CI-' + [guid]::NewGuid().ToString('N')
    if (Test-Path -LiteralPath $userMsi) { throw 'Unexpected existing MSI test registration.' }
    try {
        New-Item -Path $userMsi | Out-Null
        Set-ItemProperty -LiteralPath $userMsi -Name 'DisplayName' -Value 'Super-SAG'
        Set-ItemProperty -LiteralPath $userMsi -Name 'Publisher' -Value $publisher
        Set-ItemProperty -LiteralPath $userMsi -Name 'UninstallString' -Value '"C:\Windows\System32\msiexec.exe" /x {00000000-0000-0000-0000-000000000000}'
        Reject-Version 'per-user MSI registration refused' '0.2.9'
    } finally {
        if (Test-Path -LiteralPath $userMsi) { Remove-Item -LiteralPath $userMsi -Recurse -Force }
    }
    $admin = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    if ($admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        foreach ($view in @([Microsoft.Win32.RegistryView]::Registry32, [Microsoft.Win32.RegistryView]::Registry64)) {
            $baseKey = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, $view)
            $subkey = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SuperSAG-CI-' + [guid]::NewGuid().ToString('N')
            if ($null -ne $baseKey.OpenSubKey($subkey)) { throw 'Unexpected existing MSI test registration.' }
            $msiKey = $baseKey.CreateSubKey($subkey)
            try {
                $msiKey.SetValue('DisplayName', 'Super-SAG')
                $msiKey.SetValue('Publisher', $publisher)
                $msiKey.SetValue('UninstallString', '"C:\Windows\System32\msiexec.exe" /x {00000000-0000-0000-0000-000000000000}')
                $msiKey.Close()
                Reject-Version "MSI registration refused ($view)" '0.2.9'
            } finally {
                $msiKey.Dispose()
                $baseKey.DeleteSubKeyTree($subkey, $false)
                $baseKey.Dispose()
            }
        }
    } else {
        Write-Host 'MSI registry-view test skipped: runner is not an administrator.'
    }
    $otherDir = Join-Path $smoke 'different-install-directory'
    Reject-Version 'recognized build with different installation directory refused' '0.2.9' $otherDir
    if (Test-Path -LiteralPath $otherDir) { throw 'The refused different destination was created.' }
    Set-ItemProperty -LiteralPath $uninstall -Name 'DisplayVersion' -Value '0.2.9'
    if ((Invoke-Setup $installDir) -ne 0) { throw 'The specifically recognized test build was not upgraded.' }
    $newIdentity = & $cli --build-info | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $newIdentity.version -ne '0.1.0' -or $newIdentity.channel -ne 'release' -or
        [IO.File]::ReadAllText($dataMarker) -ne 'test data preserved') {
        throw 'The recognized test build did not upgrade while preserving test data.'
    }
    $checks.Add('recognized old test build upgraded in place; data marker preserved')

    # This profile was verified clean before the preceding smoke install. The
    # native marker tests the uninstaller's real APPDATA location, not just an
    # environment-variable override used by the application.
    $nativeData = Join-Path $env:APPDATA 'com.sag.desktop'
    New-Item -ItemType Directory -Path $nativeData -Force | Out-Null
    $nativeMarker = Join-Path $nativeData 'super-sag-ci-preserve.txt'
    if (Test-Path -LiteralPath $nativeMarker) { throw 'Unexpected existing native data marker.' }
    [IO.File]::WriteAllText($nativeMarker, 'native data preserved')
    try {
        $uninstaller = Join-Path $installDir 'uninstall.exe'
        if (-not (Test-Path -LiteralPath $uninstaller -PathType Leaf)) { throw 'Missing smoke uninstaller.' }
        $remove = Start-Process -FilePath $uninstaller -ArgumentList '/S' -PassThru
        if (-not $remove.WaitForExit(120000)) { $remove.Kill(); throw 'Uninstaller timed out.' }
        if ($remove.ExitCode -ne 0) { throw "Uninstaller failed with exit code $($remove.ExitCode)." }
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        while ((Test-Path -LiteralPath $desktop) -or (Test-Path -LiteralPath $cli) -or (Test-Path -LiteralPath $uninstall)) {
            if ([DateTime]::UtcNow -gt $deadline) { throw 'Uninstaller did not remove the managed binaries and registration.' }
            Start-Sleep -Milliseconds 250
        }
        if ((Test-Path -LiteralPath $uninstall) -or -not (Test-Path -LiteralPath $product) -or
            [IO.File]::ReadAllText($nativeMarker) -ne 'native data preserved') {
            throw 'Uninstall did not preserve the expected registration and native data.'
        }
        if ((Invoke-Setup $installDir) -ne 0) { throw 'Reinstall after preserving data was refused.' }
        $reinstalledIdentity = & $cli --build-info | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0 -or $reinstalledIdentity.version -ne '0.1.0' -or
            [IO.File]::ReadAllText($nativeMarker) -ne 'native data preserved') {
            throw 'Reinstall did not preserve native data and restore the CLI.'
        }
        $checks.Add('uninstall preserving native data, followed by reinstall')
    } finally {
        if (Test-Path -LiteralPath $nativeMarker) { Remove-Item -LiteralPath $nativeMarker -Force }
    }
}
finally {
    # Only the exact files and keys created by the preceding smoke test are touched.
    try {
        if (Test-Path -LiteralPath (Split-Path -Parent $cli)) {
            Copy-Item -LiteralPath $backup -Destination $cli -Force
        }
        if (Test-Path -LiteralPath $uninstall) {
            Set-ItemProperty -LiteralPath $uninstall -Name 'DisplayVersion' -Value $originalVersion
        }
    } catch {
        $cleanupError = $_
        Write-Warning "Could not restore a disposable smoke fixture: $($_.Exception.Message)"
    } finally {
        [Environment]::SetEnvironmentVariable('SUPER_SAG_INSTALLER_TEST_MODE', $oldTestMode, 'Process')
        [Environment]::SetEnvironmentVariable('SAG_DATA_DIR', $oldDataDir, 'Process')
        [Environment]::SetEnvironmentVariable('SAG_DESKTOP_DATA_DIR', $oldDesktopDataDir, 'Process')
    }
}
if ($cleanupError) { throw 'Failed to restore a disposable smoke fixture.' }
[ordered]@{status='passed'; scope='actual NSIS silent installer; simulated prior registration and CLI'; checks=$checks} | ConvertTo-Json -Depth 4
