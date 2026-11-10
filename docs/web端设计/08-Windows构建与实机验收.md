# 08 Windows 构建与实机验收

状态：源码和步骤准备中；**尚未在 Windows 上构建、安装或验证覆盖升级**。本页为执行清单，不是通过证明。Super-SAG 先行构建版本号为 `0.2.8`；它高于用于升级对照的 SAG-Wiki `0.2.7`，不表示已有正式发行。

## 1. 仓库与环境

目标为公开仓库 `https://github.com/CalmBuilder/Super-SAG`。原版安装包为本地对照材料，不随新仓库分发；保留并核对用户已有安装包的 SHA-256：`2c0b15e646b824c5503f4f431f54dc807b75acce9ca2f73b18b5f67c9b844d57`。`pros/SAG-Wiki` 是固定参考子模块，并非旧 Web 原型。

在 Windows x64 上准备 Git、Node.js（本次 Linux 前端验证为 Node 24）、Rust stable MSVC 工具链、Microsoft C++ 构建工具、WebView2 和网络；Tauri 构建会按需取得 NSIS 工具。记录实际版本。首次克隆完成后，PowerShell 从新目录执行：

```powershell
git -c core.autocrlf=false clone https://github.com/CalmBuilder/Super-SAG.git
Set-Location Super-SAG
git config --local core.autocrlf false
git -c core.autocrlf=false submodule update --init --recursive
git status --short --branch
git rev-parse HEAD
git submodule status
node --version
npm.cmd --version
rustc --version
cargo --version
rustup show active-toolchain
```

若已经克隆，先检查工作区有无个人改动，再执行 `git pull --ff-only` 和 `git -c core.autocrlf=false submodule update --init --recursive`；不要用重置命令覆盖本地文件。正式验收时记下实际提交、子模块提交、锁文件摘要、Windows 版本、显示缩放、语言及主题。

## 2. 构建安装程序

在仓库根目录运行；任一步失败时保留日志并停止，先反馈失败原因，不执行安装：

```powershell
npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
npm.cmd run check
if ($LASTEXITCODE -ne 0) { throw 'frontend check failed' }
npm.cmd run package:windows
if ($LASTEXITCODE -ne 0) { throw 'Windows packaging failed' }
Get-ChildItem .\src-tauri\target\release\bundle\nsis\*.exe
```

最后一条应列出新生成的 Super-SAG NSIS 安装程序；以实际路径、版本和构建时间为准，不能把已有原版安装包当作新产物。对实际新文件执行：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '<实际新安装程序路径>'
Get-AuthenticodeSignature -LiteralPath '<实际新安装程序路径>' | Select-Object Status, StatusMessage, SignerCertificate
```

在替换尖括号占位符时使用实际路径，记录摘要和签名状态。不要把 API 密钥、用户目录或私有资料放入日志或截图。新的独立发布签名和自动更新通道尚未配置；应用内更新暂不可用。Tauri CLI 固定版本与自定义安装器模板不匹配时，构建会停止，必须先审查模板差异。

## 3. 隔离安装与覆盖升级

1. 使用隔离 Windows 环境或专用测试用户，不操作唯一业务数据。准备虚构的多层目录、多格式文件及备份，记录原件 SHA-256 和配置；准备默认数据目录、`SAG_DATA_DIR` 和 `SAG_DESKTOP_DATA_DIR` 场景，不把密钥写入证据。
2. 先用原版 `0.2.7` 安装器安装，在其中添加虚构目录、构建索引，建立设置、会话和笔记。记录安装路径、卸载注册信息、快捷方式、实际 CLI/服务版本及 build ID，以及可恢复备份。不得把原版的安装结果当作新包结果。
3. 在隔离环境运行新 Super-SAG 安装器。升级界面应默认选择保留现有安装的选项；确认实际选项含义后操作，不选择删除应用数据。检查安装位置、卸载入口、原版快捷方式与新图标、进程和日志；若路径或选项不符合预期，停止并记录，不继续覆盖。
4. 安装后验证无需登录，旧设置、文件夹、索引、会话、笔记和原文件可用；用相同数据核查文件读写、目录选择、多格式、忽略、索引更新、快速和深入搜索、Jev、问答、流式回答及引用、设置、快捷搜索、托盘、CLI/Agent。使用可控模型和可用时的真实模型分别记录，隐藏密钥。
5. 在另一个隔离状态验证全新安装、重复安装、重启、Windows 账户及自定义数据目录；再检查运行中升级、文件占用、失败恢复和卸载。确认非本程序快捷方式不被删除；删除索引或移除目录不删除原文件。CLI/服务同时记录实际可执行路径、版本、build ID、协议和连接结果。
6. 按正常、极值、边界、失败/恢复分别记录预期、实际、系统、输入文件摘要、脱敏截图及未通过项。完成后回传结果与新安装包 SHA-256；不能以安装界面截图、HTTP 成功或旧安装包代替新包的业务验收。

全部必选项通过后，冻结新安装包、源码和测试资料作为正式 Web 对照基准。任一项未测或失败都保留为待验收，不推进为 Windows 阶段通过。
