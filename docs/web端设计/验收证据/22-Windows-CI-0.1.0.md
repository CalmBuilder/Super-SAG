# 初始化提交的 Windows 云端构建记录

日期：2026-11-11。该记录只对应初始化提交 `3b90cc028b3eaf4ff2b108797b90c2f57df0ec01`，不代表后续修改也已通过。

- [GitHub Actions 运行 42863014667](https://github.com/CalmBuilder/Super-SAG/actions/runs/42863014667)：成功，环境为 Windows 2025、Node.js 24.22.1 和 Rust 1.98.1。
- 生成 `Super-SAG_0.1.0_x64-setup.exe`；该次云端文件的 SHA-256 是 `63D1138EC842793C2A33DFCAB51D6BFDE3BDCE814374D382382A9EBB285BC2F7`。该文件未发布；本地另行编译的文件需单独计算哈希，不能假定字节相同。
- 在干净 runner 中静默安装、核对版本、启动桌面进程及其隔离服务；运行安装包内 CLI 指南，检索使用本地 Jev 夹具。已识别旧构建与未知较新构建的 CLI 安装记录为合成数据。
- 静默流程未验收安装向导、真实快捷方式、任务栏、用户 Windows 的旧数据覆盖升级、真实模型和真实 Agent。该提交随后发现未识别版本的安装器保护及品牌遗漏，需要在修复后重新构建和验证。
