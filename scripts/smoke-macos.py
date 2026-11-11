#!/usr/bin/env python3
"""Smoke-test a built macOS DMG on a disposable GitHub-hosted runner.

This checks native process startup, its isolated service, and whether its
window can be raised; it does not validate business interactions, distribution
signing, notarization, or a user's machine.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
WINDOW_PROBE = r'''
import Foundation
import CoreGraphics
let target = Int32(CommandLine.arguments[1])!
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
let owned = windows.filter { window in
    (window[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value == target &&
    (window[kCGWindowLayer as String] as? NSNumber)?.intValue == 0
}
print(owned.count)
'''


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_native_window(process, temporary):
    swift_source = temporary / 'windows.swift'
    swift_source.write_text(WINDOW_PROBE)
    window_probe = temporary / 'windows'
    run('swiftc', str(swift_source), '-o', str(window_probe), timeout=90)
    deadline = time.monotonic() + 45
    last_error = 'no on-screen window'
    while time.monotonic() < deadline and process.poll() is None:
        result = run(str(window_probe), str(process.pid), timeout=15)
        value = result.stdout.strip()
        if value.isdigit() and int(value) > 0:
            statement = f'tell application "System Events" to tell (first application process whose unix id is {process.pid}) to perform action "AXRaise" of window 1'
            try:
                run('osascript', '-e', statement, timeout=15)
                probe = subprocess.run([str(Path(os.environ['RUNNER_TEMP']) / 'native-ax-probe'), str(process.pid)],
                                       text=True, capture_output=True, timeout=30)
                print('ACCESSIBILITY_PROBE', probe.returncode, probe.stdout[-16000:], probe.stderr[-1000:])
                return {'on_screen_windows': int(value), 'accessibility_raise': True}
            except subprocess.CalledProcessError as error:
                last_error = (error.stderr or str(error))[-500:]
            except subprocess.TimeoutExpired:
                last_error = 'System Events timed out'
        time.sleep(1)
    raise RuntimeError(f'The desktop window was not visible and accessible: {last_error}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", choices=("arm64", "x86_64"), required=True)
    args = parser.parse_args()
    require(sys.platform == "darwin" and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
            and os.environ.get("RUNNER_TEMP"),
            "Run only on a disposable GitHub-hosted macOS runner")
    require(platform.machine() == args.arch, "Runner architecture does not match requested native architecture")
    version = json.loads((ROOT / "package.json").read_text())["version"]
    dmgs = sorted((ROOT / "src-tauri/target/release/bundle/dmg").glob("Super-SAG*.dmg"))
    require(len(dmgs) == 1, f"Expected one Super-SAG DMG, found {len(dmgs)}")
    dmg = dmgs[0].resolve()
    digest = hashlib.sha256(dmg.read_bytes()).hexdigest()

    # A GUI startup can resolve Documents through macOS instead of HOME.
    # Refuse to run on an existing profile, even though the runner is disposable.
    home = Path.home()
    for relative in ("Documents/super-sag", "Documents/sag-wiki", "Library/Application Support/com.sag.desktop",
                     ".local/bin/sag", ".local/bin/super-sag", ".claude/skills/sag", ".claude/skills/super-sag",
                     ".agents/skills/sag", ".agents/skills/super-sag", ".config/opencode/skills/sag",
                     ".config/opencode/skills/super-sag"):
        require(not (home / relative).exists(), f"Runner profile is not clean: {relative}")

    with tempfile.TemporaryDirectory(prefix="super-sag-macos-", dir=os.environ["RUNNER_TEMP"]) as temp:
        temporary = Path(temp).resolve()
        mount = temporary / "mount"
        mount.mkdir()
        installed = temporary / "Applications/Super-SAG.app"
        installed.parent.mkdir()
        data = temporary / "data"
        data.mkdir()
        (data / "cli-initialized").write_text("1")
        fake_home = temporary / "home"
        (fake_home / "Documents").mkdir(parents=True)
        environment = os.environ.copy()
        environment.update(HOME=str(fake_home), SAG_DATA_DIR=str(data), SAG_DESKTOP_DATA_DIR=str(data))
        attached = False
        process = None
        cli = installed / "Contents/Resources/bin/sag"
        try:
            run("hdiutil", "attach", str(dmg), "-readonly", "-nobrowse", "-mountpoint", str(mount))
            attached = True
            run("ditto", str(mount / "Super-SAG.app"), str(installed))
            info = plistlib.loads((installed / "Contents/Info.plist").read_bytes())
            require(info.get("CFBundleShortVersionString") == version, "App version does not match package version")
            require(info.get("CFBundleIdentifier") == "com.sag.desktop", "Unexpected app identifier")
            desktop = installed / "Contents/MacOS" / info["CFBundleExecutable"]
            require(desktop.is_file() and cli.is_file(), "Installed app or bundled CLI is missing")
            for binary in (desktop, cli):
                architectures = run("lipo", "-archs", str(binary)).stdout.split()
                require(args.arch in architectures, f"{binary.name} lacks {args.arch}")
            run("codesign", "--verify", "--deep", "--strict", str(installed))
            try:
                policy = subprocess.run(["spctl", "--assess", "--type", "execute", "--verbose=2", str(installed)],
                                        text=True, capture_output=True, timeout=30)
                assessment = {"exit_code": policy.returncode, "result": (policy.stderr or policy.stdout).strip()[-500:]}
            except subprocess.TimeoutExpired:
                assessment = {"result": "spctl assessment timed out"}
            cli_version = run(str(cli), "--version", env=environment).stdout.strip()
            require(cli_version == f"sag {version}", f"Unexpected bundled CLI version: {cli_version}")
            identity = json.loads(run(str(cli), "--build-info", env=environment).stdout)
            require(identity["version"] == version and identity["channel"] == "release", "Incorrect CLI build identity")

            with (temporary / "desktop.log").open("w+") as log:
                process = subprocess.Popen([str(desktop)], cwd=installed, env=environment, stdout=log, stderr=log)
                deadline = time.monotonic() + 60
                endpoint = data / "sag-service.json"
                while not endpoint.exists() and time.monotonic() < deadline:
                    if process.poll() is not None:
                        break
                    time.sleep(.25)
                if not endpoint.exists() or process.poll() is not None:
                    log.flush()
                    log.seek(0)
                    raise RuntimeError(f"Desktop did not start an isolated service: {log.read()[-4000:]}")
                time.sleep(3)
                require(process.poll() is None, "Desktop exited immediately after service startup")
                service = json.loads(run(str(cli), "service", "status", env=environment).stdout)
                require(service["version"] == version and Path(service["data_directory"]).resolve() == data,
                        "Desktop connected to an unexpected service or data directory")
                window = verify_native_window(process, temporary)

            print(json.dumps({"status": "passed", "runner": platform.platform(), "architecture": args.arch,
                              "version": version, "dmg_sha256": digest, "installed_from_dmg": True,
                              "signature": "local ad-hoc signature integrity only",
                              "spctl_assessment": assessment,
                              "native_window": window,
                              "scope": "DMG copy, native app process, isolated service and native window raise",
                              "not_verified": ["window business interactions", "real model", "physical Mac", "Developer ID", "notarization"]}, indent=2))
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            try:
                if cli.is_file() and (data / "sag-service.json").exists():
                    run(str(cli), "service", "stop", env=environment)
            finally:
                if attached:
                    run("hdiutil", "detach", str(mount))


if __name__ == "__main__":
    main()
