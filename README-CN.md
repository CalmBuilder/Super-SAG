<p align="center"><img src="assets/branding/super-sag-icon.svg" alt="Super-SAG" width="112" /></p>
<h1 align="center">Super-SAG</h1>
<p align="center"><a href="README.md">English</a> · 简体中文</p>

Super-SAG 基于 [SAG-Wiki](https://github.com/Zleap-AI/SAG-Wiki)，面向个人和 Agent 提供本地知识库。Windows 桌面版以原有文件夹、索引、搜索、问答、文件、设置和 CLI 体验为基准，使用 Super-SAG 名称和标识。

**当前状态：**Windows 源码和安装器正在准备，尚未发布 Super-SAG 安装包，也未完成 Windows 实际安装与覆盖升级验收。`0.2.8` 是构建候选版本，不代表已发布。独立签名更新通道建立前，应用内自动更新暂不可用。

![使用虚构测试数据的桌面界面](docs-site/public/images/product-ask-home-cn.png)

图片由浏览器测试替身生成，不能作为 Windows 原生验收证据。原文件保留在原目录；需要模型的检索和问答使用用户配置的服务。

## 在 Windows 上构建

准备 Git、Node.js、Rust stable 的 Windows MSVC 工具链、Microsoft C++ 构建工具及 WebView2；构建时需联网获取依赖和 NSIS。在 PowerShell 中执行：

```powershell
git -c core.autocrlf=false clone https://github.com/CalmBuilder/Super-SAG.git
Set-Location Super-SAG
git config --local core.autocrlf false
git -c core.autocrlf=false submodule update --init --recursive
npm.cmd ci
npm.cmd run check
npm.cmd run package:windows
```

安装器预计位于 `src-tauri/target/release/bundle/nsis/`，以实际构建输出为准，并记录其 SHA-256。任一步失败应停止排查。安装前请阅读 [Windows 构建与实机验收清单](docs/web端设计/08-Windows构建与实机验收.md)。覆盖升级必须先在隔离环境中使用备份和测试数据演练，不要覆盖唯一一份业务数据。

## 项目顺序

1. 完成并验收 Windows 桌面版，包括全新安装和从原版覆盖升级。
2. 以验收通过的 Windows 安装版为基准，先完成 Linux Web 样式与交互，再逐项接通业务。
3. Web 对齐后增加用户、租户和授权。旧 Web 原型只复用权限设计和测试经验，旧代码与数据库不迁入。

当前浏览器夹具仅用于开发预览，使用虚构响应，并非 Web 服务。方案和验收记录见 [docs/web端设计](docs/web端设计/README.md)，中英文使用文档见 [docs-site](docs-site/README.md)。

## 上游与许可

Super-SAG 基于 [SAG-Wiki](https://github.com/Zleap-AI/SAG-Wiki)，保留原项目署名和第三方许可。详见 [LICENSE](LICENSE) 与 `src-tauri/licenses/`。初始化子模块后，可在固定参考 `pros/SAG-Wiki` 查看上游历史 README。
