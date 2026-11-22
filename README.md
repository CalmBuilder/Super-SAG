<p align="center"><img src="assets/branding/super-sag-icon.svg" alt="Super-SAG" width="112" /></p>

# Super-SAG

English · [简体中文](README-CN.md)

Super-SAG provides desktop, CLI and browser access to a shared knowledge base. Add folders to index and search documents, configure models for questions, and use the CLI or API with agents.

Download the Windows x64 installer and macOS Apple Silicon / Intel test installers from [Super-SAG v0.1.0](https://github.com/CalmBuilder/Super-SAG/releases/tag/v0.1.0). Windows is unsigned; the macOS builds are ad-hoc signed and not notarized.

## Documentation

- [Installation](docs-site/content/docs/installation.en.mdx)
- [CLI](docs-site/content/docs/cli.en.mdx)
- [Web service](docs-site/content/docs/remote-access.en.mdx)
- [Development](docs-site/content/docs/development.en.mdx)

Desktop and CLI builds share the same service and local knowledge base. The web service can be configured to listen on a local network address; connect using the host's actual IP address.

### Web/B/S quick start

The Web version is not a separately deployed frontend: the host running `super-sag` owns the background service, index, settings, and knowledge-base data, while the CLI serves the embedded browser assets. The desktop window is optional; the host service must remain running.

With a desktop installation, enable **Settings → Remote services → Web service** and open the address shown there. On a server or headless host, run:

```sh
# Optional: choose the knowledge-base directory for this host
export SAG_DATA_DIR="$HOME/.local/share/super-sag"

# Add and index a host directory on first deployment
super-sag add /srv/super-sag-library
super-sag list

# Start the browser service on the LAN; the default port is 24681
super-sag api web access-code on
super-sag api web start --host 0.0.0.0 --port 24681
super-sag api status
```

Open the local or LAN address printed by `api status`; do not use `0.0.0.0` as the browser URL. When access-code protection is enabled, enter the value printed by `super-sag api web code`. Stop the browser service with `super-sag api web stop`; stop the whole background service only when needed with `super-sag service stop`. Running `super-sag api start` by itself enables HTTP API/MCP but does not replace `api web start` or serve the Web page.

For a source deployment, run `npm ci && npm run build:cli` in the repository root, then run `./src-tauri/bin/sag install cli` to install the command under the current user's `~/.local/bin`; open a new terminal before using the `super-sag` commands above. The build embeds the `dist-web` assets in the CLI, so no separate Node/Vite Web server is required. To start it after reboot, run `super-sag api autostart enable` after enabling the Web service.

The built-in HTTP service has no TLS. Use it only on a trusted LAN or behind a controlled reverse proxy, and keep access-code and firewall restrictions enabled. See the [Web service guide](docs-site/content/docs/remote-access.en.mdx) for uploads, external URLs, API keys, and proxy configuration.

## Development

Install Node.js and Rust, then run `npm ci` and `npm run check`. Windows installers use `npm run package:windows` in a configured Windows build environment. A standalone npm package and an independent signed update channel have not been published.

Third-party licenses are retained in `src-tauri/licenses/` and the relevant dependency directories.
