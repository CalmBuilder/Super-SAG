# macOS 原生构建与启动检查

日期：2026-11-11。[GitHub Actions 运行 42955911704](https://github.com/CalmBuilder/Super-SAG/actions/runs/42955911704) 使用验证提交 `5e30e3e6effafb91397d7b0aa5421234b1a6aafe`，其桌面产品代码基于 `9459f4b90617a2042d20848eea6560e0d6812ebe`。运行于 GitHub 托管的 macOS 虚拟机，非物理设备。

## Apple 芯片 arm64

- **通过范围**：macOS 15.8.2 原生构建 `v0.1.0` app 和 DMG，检查应用版本、标识、芯片架构、打包资源及临时签名完整性；从 DMG 复制到隔离目录后直接启动应用进程和隔离服务。
- 测试用 DMG SHA-256：`28ebc2081c6e04bc61845d8079480ee4e9c46765f594f5b8478ec1f706f1297e`。该文件仅用于云端本次测试，并未发布；其他构建必须单独计算摘要。
- 随包 CLI 在隔离 HOME 和数据目录使用真实临时文件验证添加、索引、目录列表、移除及重新添加、服务重启、原文件保留；验证三类 Agent Skill 安装与重复安装，非法 Agent、未托管 Skill、搜索条数 0/1/5/100/101 及本地接口 404/405 等边界。搜索中的 Jev 使用本地协议替身，未运行真实 Agent 或真实模型。
- 普通构建未提供 Safari 扩展安装包，日志确认其导出被禁用。

## Intel x86_64

同一运行中的 Intel 构建和后续检查尚在执行；结果未出前不标为通过。

## Safari 扩展源码检查

[GitHub Actions 运行 42958141733](https://github.com/CalmBuilder/Super-SAG/actions/runs/42958141733) 使用验证提交 `b5253434d5b19ba292e10571c31187c14c209e54`。Apple 芯片和 Intel 的 macOS 15 中，Swift 文件保存和新旧默认目录测试均通过，包括中文内容、嵌套目录、不覆盖及路径边界；本地临时签名的 Safari 开发 app 和 DMG 构建及签名完整性检查均通过。

上述构建早于中文引导标题的品牌修正；修正后另行启动[运行 42959347462](https://github.com/CalmBuilder/Super-SAG/actions/runs/42959347462)，基于提交 `15193f946bbb1543a24f2e05f4696c3f72ee6845` 检查两种芯片及实际包中的标题。Apple 芯片和 Intel 的源码测试、开发包构建与包内中文标题检查均通过。开发测试包不是桌面应用内的已公证 Safari 扩展，尚未验证 Safari 实际启用和网页剪藏。

## 不在通过范围内

Finder 安装交互、窗口及菜单操作、物理 Mac、真实模型问答和引用、真实 Agent 调用、旧数据升级、Developer ID 签名、公证、Gatekeeper、Safari 扩展安装和实际使用均未完成验收。临时签名和 CI 单次启动不能证明正式分发或整个 macOS 产品可用。
