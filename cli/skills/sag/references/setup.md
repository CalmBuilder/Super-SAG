# Knowledge base, configuration and installation

The Super-SAG CLI and desktop app share the same local service, knowledge base, settings and credentials. Search automatically uses registered folders within the requested directory, or the requested subtree of a registered root. There is no per-folder CLI authorization setting.

## First-use setup

When asked to install this Skill and enable SAG for a project, complete the applicable steps yourself. Use the CLI bundled with Super-SAG; a separate Super-SAG npm package is not currently published.

1. Run `super-sag --version`. Reuse an existing compatible Super-SAG installation. If the command is missing, start the Super-SAG desktop app and allow its bundled CLI setup to complete, then open a new terminal. The bundled Windows executable can also install itself explicitly:

   ```bash
   & "<Super-SAG install folder>\bin\sag.exe" install cli
   super-sag --version
   ```

   The placeholder is the actual installation folder, not a literal path. Report a missing desktop installation or CLI setup failure directly. Do not silently replace a foreign or user-modified CLI, and use only the bundled Super-SAG build.

2. Install the current Skill folder for the active agent at the [location below](#installation-and-removal), including `SKILL.md` and all three references: `setup.md`, `parameters.md`, and `ignores.md`. Retrieve all four files from the source URL the user supplied; save a local `super-sag.md` entry as `SKILL.md` and keep the `references/` subdirectory. When no source was supplied, use `super-sag install` for the requested agent to install the bundled snapshot. Preserve user-edited files and unrelated skills. A new agent session loads it automatically; use the instructions already read to finish the current setup.

3. Run `super-sag config --if-needed` to reuse existing Jev settings. For a user-supplied unauthenticated Jev service, configure `--auth none` as described below. If Bearer authentication needs a key, have the user run `super-sag` in an interactive terminal and enter their Jev endpoint, model and API key there. The key input is hidden. If credentials were already supplied through a secure local source, use `super-sag config --key-stdin` as described below. Do not request keys in chat. Only the Jev retrieval configuration is required for CLI semantic search; a desktop answer model is unnecessary.

4. From the intended project directory, run `super-sag check --json`. If coverage is `none`, inspect the project formats and run `super-sag add --types md,txt,html,py,js,ts,tsx,json,yaml` with the extensions needed for that project, then check again. Use `super-sag add --help` to check whether the installed CLI supports `--types`; use the owning installer to update an older managed CLI. For `partial`, inspect `super-sag list` and the intended scope; retain explicitly excluded subtrees. For `excluded` or disabled CLI access, report the existing setting and change it only when the user's request authorizes that change. Wait for pending indexing; report file errors or an empty index instead of searching unrelated directories.

5. Confirm the installed version, all four Skill files, usable Jev configuration and `super-sag check` readiness with at least one indexed file. Verify one semantic search using the user's question or a specific question about that project. Report completion with the searched project and verification result. If user credential entry is still pending, report that remaining step explicitly; CLI and Skill installation alone do not establish search readiness.

## Directory and status commands

| Command | Meaning |
| --- | --- |
| `super-sag status` | Show service connection, build version, protocol version, process, executable, CLI access and JEV configuration. It does not inspect directory coverage or start a stopped service. |
| `super-sag list [--json]` | List all registered roots with status, indexed file count and errors. JSON is an array; no roots gives an empty array. |
| `super-sag check [DIRECTORY] [--json]` | Check the current or specified directory's coverage, readiness, CLI access, indexed file count and relevant roots. |
| `super-sag add [DIRECTORY] [--types EXT,...] [--json]` | Add or update the directory and start indexing. `--types` selects text and built-in document extensions, such as `md,html,py,ts,json,docx,pdf,xlsx`; a leading dot and uppercase are accepted. Omit it to retain existing settings. JSON includes `path`, `index_status` and `cli_authorized`. |
| `super-sag remove [DIRECTORY] [--json]` | Remove a registered root or its subtree from the knowledge base; local files remain. JSON returns `path`. |

Only `check`, `add` and `remove` accept a directory argument. `status` and `list` do not. Relative paths resolve from the current directory.

`check` JSON includes `path`, `coverage`, `index_ready`, `enabled`, `indexed_files` and `roots`, plus `extensions` for an included directory. `extensions` lists the text and built-in document formats enabled at that directory; child folders may have their own overrides. Coverage is `included`, `partial` (only child roots are registered), `excluded` or `none`. `indexed_files` is the actual count within the checked directory. A registered root with zero indexed files has no searchable content. Root status values include `pending`, `indexing`, `ready`, `partial` (some files failed) and `error`; root indexing status and directory coverage are separate fields. Exit codes are in [parameters](parameters.md#output-and-exit-codes).

`--types` is an extension allowlist for that folder, saved in the managed index-options block of `.sagignore`. Changing it rescans the folder and removes unselected files from the index; original files and handwritten ignore rules remain. Explicit child-folder settings retain precedence. Ignore rules continue to apply. Unknown extensions are rejected. Text, code and built-in document formats are supported; this option turns off optional Docling-only formats for that folder. With no saved folder settings, plain `super-sag add` inherits global defaults: Markdown, text, RTF, Office, spreadsheets, EPUB and text-based PDFs enabled; code and configuration disabled. Built-in documents need no component download. PDFs requiring OCR use an installed Docling, or report an actionable indexing error when it is absent.

When the task's project is unindexed, run `super-sag add` with the required project extensions in its directory yourself. Check `super-sag check`; if indexing is still in progress, wait for it to finish before searching. No sync flag is needed. Add only the intended project, preserving existing exclusions. Do not add unrelated projects or broaden to a parent directory merely to find more results.

Removing a root unregisters it. Removing a subtree keeps it excluded from future scans and file watching. Restore a removed subtree only when requested, with `super-sag add` for that same subtree. A moved or offline registered root can still be removed using its original absolute path.

## Model configuration and access

Running `super-sag` without a query in an interactive terminal guides first-time JEV setup; with existing configuration, it shows help. Noninteractive calls do not prompt. Semantic search needs JEV configuration; local matching, index management and service inspection do not need a model key.

| Command or option | Meaning |
| --- | --- |
| `super-sag config` | In a terminal, prompt for endpoint, model and a hidden key when using Bearer authentication; Enter keeps existing values. No-authentication services need no key. Noninteractive invocation reads the current configuration. Output is JSON without the key. |
| `super-sag config --if-needed` | With no replacement options, reuse a usable Bearer or no-authentication configuration; otherwise guide terminal setup. Noninteractive Bearer use without a key reports an error. |
| `super-sag config --url URL` | Set the JEV endpoint. |
| `super-sag config --model MODEL` | Set the JEV model. |
| `super-sag config --auth none` | Explicitly use a Jev service without authentication; remove its saved key and omit the authorization header. |
| `super-sag config --auth bearer` | Use API Key authentication (the default for existing settings). Supply the service’s key when switching back from `none`. |
| `super-sag config --key-stdin` | Read the key from standard input. |
| `super-sag config --key KEY` | Set a key through a command argument; it may appear in shell history and process arguments. Mutually exclusive with `--key-stdin`. |
| `super-sag config --enable` | Re-enable CLI access when the user explicitly requests it. There is no `--disable` CLI option. |

Options may be combined. Prefer hidden terminal input or `--key-stdin`; never print credentials. Use the user's endpoint, model and credentials, and preserve existing configuration unless the user requests a change. For example, when those environment variables and a key file have already been supplied:

```bash
super-sag config --url "$JEV_URL" --model "$JEV_MODEL" --key-stdin < "$JEV_KEY_FILE"
```

For a user-supplied local Jev service that requires no authentication, configure `super-sag config --url "$JEV_URL" --model "$JEV_MODEL" --auth none`; verify the installed CLI supports `--auth` with `super-sag config --help`. The URL may be a base URL or a complete `/systemone` or `/decisions` endpoint. Choose `none` only when the user identifies the service as unauthenticated.

If Bearer setup is required and credentials have not been supplied, ask the user to run `super-sag` in a terminal. Never invent credentials or silently change providers. If CLI access is off, report that setting; do not enable it without the user's request.

## Service commands

| Command | Meaning |
| --- | --- |
| `super-sag service status` | Print service metadata as JSON when running, or report that it is stopped. Does not start it. |
| `super-sag service stop` | Stop the shared service; already stopped is successful. |
| `super-sag service restart` | Stop it if running, then start it and print service metadata as JSON. |

Search and management commands that need the core start or reuse the service automatically. Stopping or restarting affects desktop and CLI requests sharing that service; run these actions when requested or necessary for an authorized service update. The internal `super-sag service serve` command runs the service in the foreground for startup diagnostics; normal use does not require it. Service subcommands do not accept `--json` or a directory.

## Installation and removal

The commands below manage the Super-SAG executable installation or bundled Skill snapshot. Do not remove or overwrite separately managed CLI installations without the user's instruction.

```bash
super-sag install cli
super-sag install codex
super-sag install claude-code
super-sag install opencode
super-sag uninstall codex
super-sag uninstall cli
```

`super-sag install TARGET` and `super-sag uninstall TARGET` require exactly one target: `cli`, `codex`, `claude-code` or `opencode`.

- `cli` installs the executable into `~/.local/bin` (`sag.exe` on Windows) and configures the terminal path. Open a new terminal if the current one has not picked up the change.
- `codex` installs the skill and its references into `~/.agents/skills/super-sag`.
- `claude-code` installs into `~/.claude/skills/super-sag`.
- `opencode` installs into `~/.config/opencode/skills/super-sag`.

Run installation or removal for the requested target only. Repeat installation updates SAG-managed files. The installer preserves foreign or edited files and reports ownership conflicts; do not bypass those checks. Uninstall removes managed installation files, while leaving project files and the knowledge base intact. Restart the relevant agent session to load an updated skill.

## Help and failures

Use `super-sag --help` / `super-sag help` for the command list, `super-sag <command> --help` / `super-sag help <command>` for a command, and `super-sag service <action> --help` for service actions. `super-sag -V` / `super-sag --version` shows the CLI version; `super-sag status` also identifies the running service build. Internal `super-sag --build-info` emits build metadata for packaging and compatibility checks.

For an isolated test knowledge base, `SAG_DATA_DIR` selects the data directory; `SAG_DESKTOP_DATA_DIR` is the fallback environment variable. Omit both for normal shared use. Changing them selects a different knowledge base rather than adding folders to the existing one.

If a command fails, report its reason. After a relevant correction, retry only the affected operation; otherwise use normal file tools for the authorized task. Do not silently switch model providers, enable access, or replace user-edited installation files.
