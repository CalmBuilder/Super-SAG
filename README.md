<p align="center"><img src="assets/branding/super-sag-icon.svg" alt="Super-SAG" width="112" /></p>

# Super-SAG

English · [简体中文](README-CN.md)

Super-SAG provides desktop, CLI and browser access to a shared knowledge base. Add folders to index and search documents, configure models for questions, and use the CLI or API with agents.

Download the Windows x64 installer from [Super-SAG v0.1.0](https://github.com/CalmBuilder/Super-SAG/releases/tag/v0.1.0). The installer is unsigned. A macOS installer is not yet available.

## Documentation

- [Installation](docs-site/content/docs/installation.en.mdx)
- [CLI](docs-site/content/docs/cli.en.mdx)
- [Web service](docs-site/content/docs/remote-access.en.mdx)
- [Development](docs-site/content/docs/development.en.mdx)

Desktop and CLI builds share the same service and local knowledge base. The web service can be configured to listen on a local network address; connect using the host's actual IP address.

## Development

Install Node.js and Rust, then run `npm ci` and `npm run check`. Windows installers use `npm run package:windows` in a configured Windows build environment. A standalone npm package and an independent signed update channel have not been published.

Third-party licenses are retained in `src-tauri/licenses/` and the relevant dependency directories.
