<p align="center"><img src="assets/branding/super-sag-icon.svg" alt="Super-SAG" width="112" /></p>

# Super-SAG

[English](README.md) · 简体中文

Super-SAG 提供桌面、CLI 和浏览器访问方式，共用本地知识库。可添加文件夹并索引、搜索文档，配置模型进行问答，并通过 CLI 或 API 接入 Agent。

从 [Super-SAG v0.1.0](https://github.com/CalmBuilder/Super-SAG/releases/tag/v0.1.0) 下载 Windows x64 安装包。该安装包未经代码签名，macOS 安装包尚未提供。

## 文档

- [下载安装](docs-site/content/docs/installation.mdx)
- [CLI 命令](docs-site/content/docs/cli.mdx)
- [网页服务](docs-site/content/docs/remote-access.mdx)
- [开发指南](docs-site/content/docs/development.mdx)

桌面端与 CLI 共用服务和本地知识库。网页服务可以配置监听局域网，访问时使用主机的实际 IP 地址。

## 开发

准备 Node.js 和 Rust 后运行 `npm ci` 与 `npm run check`。Windows 构建环境使用 `npm run package:windows` 生成安装包。独立 npm 包和本项目签名更新通道尚未发布。

独立第三方许可保留在 `src-tauri/licenses/` 与相应依赖目录。
