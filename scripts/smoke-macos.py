#!/usr/bin/env python3
"""Smoke-test a built macOS DMG on a disposable GitHub-hosted runner.

This checks native process startup and its isolated service, not window
interaction, distribution signing, notarization, or a user's machine.
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


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


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

            print(json.dumps({"status": "passed", "runner": platform.platform(), "architecture": args.arch,
                              "version": version, "dmg_sha256": digest, "installed_from_dmg": True,
                              "signature": "local ad-hoc signature integrity only",
                              "scope": "DMG copy, native app process and isolated service startup",
                              "not_verified": ["window interaction", "real model", "physical Mac", "Developer ID", "notarization"]}, indent=2))
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
