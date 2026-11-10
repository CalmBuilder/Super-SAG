#!/usr/bin/env python3
"""Run the desktop CLI guide against real CLI/core processes in a temporary home.

Build with ``cargo build --locked --manifest-path cli/Cargo.toml`` and run this
script with ``--binary cli/target/debug/sag`` on Linux. Windows execution is
restricted to a clean GitHub-hosted runner with an explicit flag, because it
uses that disposable profile and changes its user PATH. The Jev server is the
local protocol fixture in local-jev-e2e.py, not a real inference service.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("local_jev_e2e", ROOT / "tests/local-jev-e2e.py")
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def run(binary, windows_runner=False):
    windows = os.name == "nt"
    if windows:
        require(windows_runner and os.environ.get("GITHUB_ACTIONS") == "true"
                and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted" and os.environ.get("RUNNER_TEMP"),
                "Windows test is restricted to an explicitly enabled disposable GitHub-hosted runner")
    else:
        require(os.name == "posix" and not windows_runner, "unsupported platform or flag")
    checks = []
    with tempfile.TemporaryDirectory(prefix="super-sag-cli-guide-") as temporary, fixture_module.JevFixture() as fixture:
        temporary = Path(temporary).resolve()
        home = Path(os.environ["USERPROFILE"]).resolve() if windows else temporary / "home"
        data, project = temporary / "data", temporary / "项目 space"
        if windows:
            for relative in (".local/bin/sag.exe", ".local/bin/super-sag.exe", ".local/bin/sag.sag-install.json",
                             ".local/bin/super-sag.sag-install.json", ".claude/skills/super-sag",
                             ".agents/skills/super-sag", ".config/opencode/skills/super-sag"):
                require(not (home / relative).exists(), f"runner profile is not clean: {relative}")
        else:
            home.mkdir()
        (project / "docs").mkdir(parents=True)
        source = project / "docs/checklist.md"
        source.write_text(fixture_module.DOCUMENTS["checklist.md"], encoding="utf-8")
        (project / "background.md").write_text(fixture_module.DOCUMENTS["background.md"], encoding="utf-8")
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        environment = {
            "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local/share"), "XDG_CACHE_HOME": str(home / ".cache"),
            "SAG_DATA_DIR": str(data), "SAG_DESKTOP_DATA_DIR": str(data),
            "PATH": os.pathsep.join((str(home / ".local/bin"), os.environ.get("PATH", "") if windows else "/usr/bin:/bin")),
            "LANG": "C.UTF-8", "SHELL": "/bin/bash",
        }
        if windows:
            for name in ("SystemRoot", "WINDIR", "TEMP", "TMP", "USERPROFILE", "USERNAME", "APPDATA", "LOCALAPPDATA", "COMSPEC"):
                if name in os.environ:
                    environment[name] = os.environ[name]
            require(environment.get("USERNAME"), "Windows service requires the runner's USERNAME for endpoint permissions")

        def execute(program, *args, success=True):
            process = subprocess.run([str(program), *args], cwd=project, env=environment,
                                     capture_output=True, text=True, encoding="utf-8", timeout=90)
            require((process.returncode == 0) == success,
                    f"{Path(program).name} {' '.join(args)}: exit {process.returncode}; "
                    f"stdout={process.stdout!r}; stderr={process.stderr!r}")
            return process

        execute(binary, "install", "cli")
        command = home / ".local/bin" / ("super-sag.exe" if windows else "super-sag")
        require(command.is_file(), "installation did not create super-sag")
        require(execute(command, "--version").stdout.startswith("super-sag "), "wrong command name")
        require("Usage: super-sag" in execute(command, "--help").stdout, "help did not use the new command")

        skill_root = ROOT / "cli/skills/sag"
        for agent, directory in (
            ("claude-code", ".claude/skills/super-sag"),
            ("codex", ".agents/skills/super-sag"),
            ("opencode", ".config/opencode/skills/super-sag"),
        ):
            execute(command, "install", agent)
            execute(command, "install", agent)  # Reinstallation is safe and repeatable.
            for name in ("SKILL.md", "references/setup.md", "references/parameters.md", "references/ignores.md"):
                require((home / directory / name).read_bytes() == (skill_root / name).read_bytes(),
                        f"{agent}: missing or changed {name}")
        execute(command, "install", "unknown-agent", success=False)
        checks.append("actual install commands for Claude Code, Codex and OpenCode; bundled files and repeat installation")

        if not windows:
            # Windows resolves its profile through the OS, so HOME cannot
            # safely redirect this particular foreign-file test there.
            foreign_home = temporary / "foreign-home"
            foreign = foreign_home / ".agents/skills/super-sag/SKILL.md"
            foreign.parent.mkdir(parents=True)
            foreign.write_text("user-owned skill\n", encoding="utf-8")
            foreign_env = {**environment, "HOME": str(foreign_home)}
            failed = subprocess.run([str(command), "install", "codex"], cwd=project, env=foreign_env,
                                    capture_output=True, text=True, timeout=30)
            require(failed.returncode != 0 and foreign.read_text() == "user-owned skill\n",
                    "installation overwrote an unmanaged skill")
            checks.append("unsupported agent and unmanaged skill are rejected without overwriting")
        else:
            checks.append("unsupported agent is rejected")

        try:
            configured = json.loads(execute(command, "config", "--url", fixture.origin + "/v1",
                                             "--model", fixture_module.MODEL, "--auth", "none").stdout)
            require(configured["auth_mode"] == "none", "fixture configuration failed")
            require(json.loads(execute(command, "config").stdout)["model"] == fixture_module.MODEL,
                    "config did not report the saved model")
            execute(command, "add")
            coverage = json.loads(execute(command, "check", "--json").stdout)
            require(coverage["index_ready"] and coverage["indexed_files"] == 2,
                    f"actual indexed files differ: {coverage}")
            execute(command, "check")
            roots = json.loads(execute(command, "list", "--json").stdout)
            require(len(roots) == 1 and Path(roots[0]["path"]).samefile(project), "list omitted the registered project")
            execute(command, "list")
            require("CLI 接入：true" in execute(command, "status").stdout, "CLI access is not enabled")
            service = json.loads(execute(command, "service", "status").stdout)
            require(service.get("pid"), "service status has no real process")
            checks.append("add, check, list, status, config and service status against actual indexed files")

            # The displayed 'set up:' line is an agent instruction; its URL
            # must serve the bundled entry and every relative reference.
            endpoint = json.loads((data / "sag-service.json").read_text(encoding="utf-8"))
            origin = f"http://127.0.0.1:{endpoint['port']}"
            for url_path, file in (("/super-sag.md", "SKILL.md"), ("/sag-wiki.md", "SKILL.md"),
                                   ("/references/setup.md", "references/setup.md"),
                                   ("/references/parameters.md", "references/parameters.md"),
                                   ("/references/ignores.md", "references/ignores.md")):
                with urlopen(origin + url_path, timeout=10) as response:
                    require(response.status == 200 and response.read() == (skill_root / file).read_bytes(),
                            f"skill URL failed: {url_path}")
            for method, path, expected in (("GET", "/missing", 404), ("POST", "/super-sag.md", 405)):
                try:
                    urlopen(Request(origin + path, method=method), timeout=10)
                except HTTPError as error:
                    require(error.code == expected, f"unexpected HTTP status: {error.code}")
                else:
                    raise AssertionError(f"{method} {path} should fail")
            checks.append("local agent setup URL and its three references; 404 and 405 behavior")

            question = fixture_module.QUESTION
            for scope in ([], ["./docs"]):
                process = execute(command, question, *scope, "-m", "5", "--json")
                results = json.loads(process.stdout)["results"]
                require(results and "VX-417" in results[0]["content"], "semantic retrieval missed the fixture source")
                if scope:
                    require(all(Path(item["absolute_path"]).samefile(source) for item in results),
                            "scoped retrieval returned an outside document")
            require("VX-417" in execute(command, question, "./docs", "-m", "5").stdout,
                    "human-readable search omitted the source passage")
            for count in ("1", "100"):
                execute(command, question, "./docs", "-m", count, "--json")
            for count in ("0", "101"):
                execute(command, question, "./docs", "-m", count, "--json", success=False)
            require(fixture.calls and not fixture.violations, f"local Jev fixture: {fixture.violations}")
            checks.append("semantic search, scoped search, -m 1/5/100 and rejection of 0/101 using local Jev fixture")

            execute(command, "remove", "./docs")
            removed = subprocess.run([str(command), "check", "./docs", "--json"], cwd=project, env=environment,
                                     capture_output=True, text=True, encoding="utf-8", timeout=90)
            require(removed.returncode != 0, "removed child unexpectedly remains covered")
            require(hashlib.sha256(source.read_bytes()).hexdigest() == before, "remove changed the original file")
            execute(command, "add", "./docs")
            restored = json.loads(execute(command, "check", "./docs", "--json").stdout)
            require(restored["index_ready"] and restored["indexed_files"] == 1, "child index was not restored")
            require(hashlib.sha256(source.read_bytes()).hexdigest() == before, "restore changed the original file")
            checks.append("remove ./docs and add ./docs; real original file unchanged and index restored")

            execute(command, "service", "restart")
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                checked = subprocess.run([str(command), "check", "--json"], cwd=project, env=environment,
                                         capture_output=True, text=True, encoding="utf-8", timeout=10)
                if checked.returncode == 0:
                    require(json.loads(checked.stdout)["indexed_files"] == 2, "restart changed the file count")
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("index did not become ready after service restart")
            require("VX-417" in execute(command, question, "./docs", "-m", "5").stdout,
                    "search did not work after restart")
            checks.append("service restart preserves configuration, index and search")

            # Exercise the reset boundary on a disposable Windows profile using
            # the installed release CLI. The old build's receipt is simulated;
            # this is not an in-place test of a real user's earlier installer.
            identity = json.loads(execute(binary, "--build-info").stdout)
            if windows and identity["channel"] == "release" and identity["version"] == "0.1.0":
                execute(command, "service", "stop")
                executables = [home / ".local/bin/sag.exe", home / ".local/bin/super-sag.exe"]
                receipts = [p.with_suffix(".sag-install.json") for p in executables]
                saved = {p: p.read_bytes() for p in executables + receipts}
                try:
                    for receipt in receipts:
                        data_record = json.loads(receipt.read_text(encoding="utf-8"))
                        data_record.update(version="0.2.9", build_id="release-d0ef53a3834270d4", channel="release")
                        receipt.write_text(json.dumps(data_record), encoding="utf-8")
                    execute(binary, "install", "cli")
                    for receipt in receipts:
                        current = json.loads(receipt.read_text(encoding="utf-8"))
                        require(current["version"] == "0.1.0" and current["build_id"] == identity["build_id"],
                                "known test build was not migrated to the initial release")
                    require(execute(command, "--version").stdout.strip() == "super-sag 0.1.0",
                            "migrated command did not run at the baseline version")

                    for receipt in receipts:
                        data_record = json.loads(receipt.read_text(encoding="utf-8"))
                        data_record.update(version="0.2.9", build_id="release-unknown", channel="release")
                        receipt.write_text(json.dumps(data_record), encoding="utf-8")
                    before_unknown = {p: p.read_bytes() for p in executables + receipts}
                    execute(binary, "install", "cli", success=False)
                    require(all(p.read_bytes() == value for p, value in before_unknown.items()),
                            "unknown newer build was modified")
                finally:
                    for path, value in saved.items():
                        path.write_bytes(value)
                checks.append("Windows release CLI: identified pre-baseline receipt upgrades; unknown newer receipt remains untouched (synthetic receipts)")
        finally:
            if (data / "sag-service.json").exists():
                execute(command, "service", "stop")
            if windows:
                for agent in ("claude-code", "codex", "opencode"):
                    execute(command, "uninstall", agent)
                execute(binary, "uninstall", "cli")
                # These exact directories were verified absent before this
                # disposable-runner test. Remove them only if still empty.
                for relative in (".claude/skills/super-sag", ".agents/skills/super-sag",
                                 ".config/opencode/skills/super-sag"):
                    directory = home / relative
                    if (directory / "references").is_dir():
                        (directory / "references").rmdir()
                    if directory.is_dir():
                        directory.rmdir()

    return {"status": "passed", "platform": "Windows hosted runner" if windows else "Linux",
            "jev": "local protocol fixture, not real inference",
            "checks": checks, "synthetic_source_sha256": before, "fixture_http_requests": len(fixture.calls)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--windows-hosted-runner", action="store_true")
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error(f"binary not found: {binary}")
    print(json.dumps(run(binary, args.windows_hosted_runner), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
