<p align="center"><img src="assets/branding/super-sag-icon.svg" alt="Super-SAG" width="112" /></p>

# Super-SAG

[English](README.md) · 简体中文

Super-SAG 提供桌面、CLI 和浏览器访问方式，共用本地知识库。可添加文件夹并索引、搜索文档，配置模型进行问答，并通过 CLI 或 API 接入 Agent。

从 [Super-SAG v0.1.0](https://github.com/CalmBuilder/Super-SAG/releases/tag/v0.1.0) 下载 Windows x64 安装包和 macOS Apple Silicon / Intel 测试包。Windows 安装包未签名；macOS 测试包仅使用临时签名，未经公证。

## 文档

- [下载安装](docs-site/content/docs/installation.mdx)
- [CLI 命令](docs-site/content/docs/cli.mdx)
- [网页服务](docs-site/content/docs/remote-access.mdx)
- [开发指南](docs-site/content/docs/development.mdx)

桌面端与 CLI 共用服务和本地知识库。网页服务可以配置监听局域网，访问时使用主机的实际 IP 地址。

### Web/B/S 快速启动

当前 Web 版不是需要单独部署的前端项目：运行 `super-sag` 的主机同时承担后台服务、索引、配置和知识库数据，CLI 内置并提供浏览器页面。桌面窗口可以不启动，主机上的后台服务必须保持运行。

已有桌面安装时，先在桌面端 **设置 → 远程服务** 开启 **网页服务**，再打开设置中显示的地址。服务器或无桌面环境可直接运行：

```sh
# 可选：指定这台主机使用的知识库数据目录
export SAG_DATA_DIR="$HOME/.local/share/super-sag"

# 首次部署时加入主机上的目录并等待/检查索引
super-sag add /srv/super-sag-library
super-sag list

# 开启网页服务并监听局域网；默认端口为 24681
super-sag api web access-code on
super-sag api web start --host 0.0.0.0 --port 24681
super-sag api status
```

用 `api status` 输出的本机或局域网地址访问，不要把 `0.0.0.0` 直接当作浏览器地址。网页访问码开启时，在登录页输入 `super-sag api web code` 输出的码。停止网页服务运行 `super-sag api web stop`；需要停止整个后台服务时再运行 `super-sag service stop`。单独运行 `super-sag api start` 只会启用 HTTP API/MCP，不会代替 `api web start` 打开 Web 页面。

从源码部署时，在仓库根目录执行 `npm ci && npm run build:cli`，再运行 `./src-tauri/bin/sag install cli` 安装到当前用户的 `~/.local/bin`，打开新终端后即可使用上面的 `super-sag` 命令。该构建会把 `dist-web` 页面资源嵌入 CLI，不需要另起 Node/Vite Web 服务器。需要随系统启动时运行 `super-sag api autostart enable`，然后保持网页服务已开启。

内置 HTTP 服务未配置 TLS，只应在可信局域网或受控反向代理后使用，并应保留访问码和防火墙限制。完整选项（上传、外部地址、API Key 和公网反向代理）见[网页服务文档](docs-site/content/docs/remote-access.mdx)。

## 开发

准备 Node.js 和 Rust 后运行 `npm ci` 与 `npm run check`。Windows 构建环境使用 `npm run package:windows` 生成安装包。独立 npm 包和本项目签名更新通道尚未发布。

独立第三方许可保留在 `src-tauri/licenses/` 与相应依赖目录。
