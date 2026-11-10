#!/usr/bin/env python3
"""Check installed Skills with real local agents in a disposable Linux home.

Supply --binary, --codex, --opencode and --claude executable paths. Claude's
model request is handled by a local synthetic HTTP endpoint, never a real
model. Agent discovery does not prove that an agent used search successfully.
"""

import argparse
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading


def require(value, message):
    if not value:
        raise AssertionError(message)


async def codex_skills(binary, home, environment):
    process = await asyncio.create_subprocess_exec(
        str(binary), "app-server", cwd=home / "project", env=environment,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )

    async def send(message):
        process.stdin.write((json.dumps(message) + "\n").encode())
        await process.stdin.drain()

    async def response(identifier):
        while True:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=30)
            require(line, "Codex app-server closed before responding")
            message = json.loads(line)
            if message.get("id") == identifier:
                require("result" in message, f"Codex app-server error: {message}")
                return message["result"]

    try:
        await send({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "cli-guide-test", "version": "1"}}})
        await response(1)
        await send({"method": "initialized", "params": {}})
        await send({"id": 2, "method": "skills/list", "params": {"cwds": [str(home / "project")], "forceReload": True}})
        result = await response(2)
        skills = [skill for entry in result["data"] for skill in entry["skills"]]
        expected = home / ".agents/skills/super-sag/SKILL.md"
        require(any(skill.get("name") == "super-sag" and skill.get("enabled")
                    and Path(skill["path"]) == expected for skill in skills), "Codex did not discover the installed Skill")
    finally:
        process.stdin.close()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except asyncio.TimeoutError:
            process.terminate()
            await process.wait()


class LocalModel:
    def __init__(self):
        self.requests = []
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                fixture.requests.append({"path": self.path, "skill_expanded":
                    "Run the installed `super-sag` command" in json.dumps(payload, ensure_ascii=False)})
                result = {"id": "msg_localfixture", "type": "message", "role": "assistant", "model": "fixture-model",
                          "content": [{"type": "text", "text": "local fixture response"}], "stop_reason": "end_turn",
                          "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}
                if payload.get("stream"):
                    events = [
                        ("message_start", {"type": "message_start", "message": {**result, "content": [], "stop_reason": None}}),
                        ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}),
                        ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "local fixture response"}}),
                        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
                        ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": 1}}),
                        ("message_stop", {"type": "message_stop"}),
                    ]
                    body = "".join(f"event: {name}\ndata: {json.dumps(item)}\n\n" for name, item in events).encode()
                    content_type = "text/event-stream"
                else:
                    body, content_type = json.dumps(result).encode(), "application/json"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def run(args):
    require(os.name == "posix", "This isolated-process test currently targets Linux")
    with tempfile.TemporaryDirectory(prefix="super-sag-agent-test-") as td, LocalModel() as model:
        home = Path(td).resolve()
        (home / ".codex").mkdir()
        (home / "project").mkdir()
        environment = {
            "HOME": str(home), "CODEX_HOME": str(home / ".codex"), "CLAUDE_CONFIG_DIR": str(home / ".claude"),
            "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_CACHE_HOME": str(home / ".cache"), "XDG_STATE_HOME": str(home / ".local/state"),
            "SAG_DATA_DIR": str(home / "data"), "PATH": f"{args.codex.parent}:/usr/bin:/bin", "LANG": "C.UTF-8",
            "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
            "ALL_PROXY": "http://127.0.0.1:9", "NO_PROXY": "127.0.0.1,localhost",
        }

        def execute(argv, env=environment, timeout=60):
            process = subprocess.run([str(item) for item in argv], cwd=home / "project", env=env,
                                     capture_output=True, text=True, encoding="utf-8", timeout=timeout)
            require(process.returncode == 0, f"{Path(argv[0]).name} failed: {process.stderr[:600]}")
            return process.stdout

        execute([args.binary, "install", "cli"])
        command = home / ".local/bin/super-sag"
        for agent in ("claude-code", "codex", "opencode"):
            execute([command, "install", agent])
        versions = {name: execute([binary, "--version"]).strip() for name, binary in
                    (("codex", args.codex), ("opencode", args.opencode), ("claude", args.claude))}

        asyncio.run(codex_skills(args.codex, home, environment))
        skills = json.loads(execute([args.opencode, "debug", "skill"]))
        expected = home / ".config/opencode/skills/super-sag/SKILL.md"
        require(any(skill.get("name") == "super-sag" and Path(skill["location"]) == expected
                    and "Run the installed `super-sag` command" in skill["content"] for skill in skills),
                "OpenCode did not discover the installed Skill")

        claude_env = {**environment, "ANTHROPIC_API_KEY": "fixture-only",
                      "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{model.server.server_port}",
                      "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "DISABLE_TELEMETRY": "1", "DISABLE_AUTOUPDATER": "1"}
        output = execute([args.claude, "--print", "/super-sag please summarize the setup",
                          "--model", "fixture-model", "--no-session-persistence", "--max-turns", "1"], env=claude_env)
        require("local fixture response" in output, "Claude Code did not receive its local synthetic response")
        require(any(call["skill_expanded"] for call in model.requests), "Claude Code did not expand the installed Skill")
        return {"status": "passed", "platform": "Linux", "versions": versions,
                "codex": "real app-server reports installed and enabled Skill",
                "opencode": "real debug skill lists installed Skill and its content",
                "claude": "real /super-sag expands the Skill into a request to a local synthetic model",
                "limit": "no real model inference or agent-driven search was performed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "codex", "opencode", "claude"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    for name in ("binary", "codex", "opencode", "claude"):
        value = getattr(args, name).resolve()
        if not value.is_file():
            parser.error(f"{name} executable does not exist: {value}")
        setattr(args, name, value)
    print(json.dumps(run(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
