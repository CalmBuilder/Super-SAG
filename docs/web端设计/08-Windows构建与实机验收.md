# 08 Windows 构建与实机验收

当前项目版本是 `v0.1.0`。用户于 2026-11-11 反馈 Windows 全部业务及保留数据升级已通过实机测试，并提供验收包 SHA-256 和源码提交，见[用户验收基准](验收证据/26-Windows用户验收基准.md)。具体测试环境及逐项操作明细尚待补充，不能将不同构建的哈希混为同一份证据。已有安装的版本号可能高于新序列，不应直接把语义版本大小当成数据迁移顺序；未知构建必须保持保护。

## 安全取得代码

仓库历史重新初始化后，旧克隆与新的 `main` 不再有共同提交；`git pull --ff-only` 不会自动合并。保留旧克隆中的个人改动，使用新目录克隆公开仓库，不通过强制重置覆盖旧工作区：

```powershell
git -c core.autocrlf=false clone https://github.com/CalmBuilder/Super-SAG.git Super-SAG-v010
Set-Location Super-SAG-v010
git config --local core.autocrlf false
git log -1 --oneline
node --version
rustc --version
cargo --version
```

## 构建

准备 Windows x64、Node.js 24.15.0 或更高版本、Rust MSVC 工具链、Microsoft C++ 构建工具和 WebView2；构建依赖及安装工具需联网。

新克隆目录必须先运行 `npm.cmd ci`；依赖只安装在各自目录，不能复用另一个克隆目录的 `node_modules`。安装程序对未识别的既有版本及匹配本产品标识的 MSI 安装采取保守拒绝策略；同版本静默重装也会拒绝。识别到指定测试构建时仅允许原目录覆盖，不能在安装器中先运行旧卸载器。真实旧版和已有数据升级仍需隔离环境验证；遇阻时保留原安装和数据，不要为了继续而勾选删除应用数据。

```powershell
npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
npm.cmd run check
if ($LASTEXITCODE -ne 0) { throw 'frontend check failed' }
npm.cmd run package:windows
if ($LASTEXITCODE -ne 0) { throw 'Windows packaging failed' }
Get-ChildItem .\src-tauri\target\release\bundle\nsis\*0.1.0*.exe
```

记录实际源码提交、安装包完整路径、SHA-256、Windows 版本及工具链版本。安装前备份真实数据，先在隔离账户或环境演练；不要选择删除应用程序数据。

## 验收

核查新包名称、图标、安装目录、卸载入口、窗口与版本；启动后在新终端核验 `super-sag --version`、`sag --version` 和实际执行路径。再使用虚构文件逐项验证添加、索引、搜索、问答、文件查看和编辑、设置、CLI、Agent 与错误恢复。对已有安装的迁移必须验证原始文件、索引、配置、会话、笔记及服务进程；未知版本、损坏记录、取消和无权限场景也要记录。

CI 云 Windows、模拟模型和浏览器替身各自有范围限制，不代替用户的真实 Windows、真实模型或数据保留升级验收。
