# macOS 0.1.0 测试安装包

日期：2026-11-11。用户请求使用 macOS 云端环境构建安装包。产品源码基线为 `33967c5a9830e6c581e37d979e3c0e8fae290a95`，与当时的 `main` 一致；[构建任务 42969687261](https://github.com/CalmBuilder/Super-SAG/actions/runs/42969687261) 的临时验证提交 `80ec2d287579ef348c9163bddbdc627e8336dcdc` 相对该基线只调整 CI 工作流，未改产品源码。两个包为临时 Actions 测试产物，未加入 GitHub Release；运行中的验证详情以任务实际结果为准。

## Apple 芯片 arm64

- 生成 `Super-SAG_0.1.0_aarch64.dmg`，大小 `16938577` 字节，SHA-256：`4987c513eb2b6cdaa647d6e449cc1bdf7adf180c696375ed056d49626f99d16c`。本机取回后摘要校验通过，并确认存在 UDIF `koly` 尾部标识。
- [Apple 芯片测试工件](https://github.com/CalmBuilder/Super-SAG/actions/runs/42969687261/artifacts/13833607421)需登录 GitHub 并具有仓库读取权限，有效期至 2026-11-18 14:18:31（北京时间）。
- macOS 15.8.2 虚拟机完成包内容、架构、版本、签名完整性、从 DMG 复制并启动应用和隔离服务、随包 CLI 与真实临时文件检查。另从保存的同一个 DMG 执行[主程序窗口检查 42971685221](https://github.com/CalmBuilder/Super-SAG/actions/runs/42971685221)，确认屏幕上有窗口且辅助功能 `AXRaise` 可执行；该检查不覆盖窗口里的业务操作。
- 应用使用 ad-hoc 临时签名，`TeamIdentifier` 未设置；上述窗口检查中 `spctl --assess --type execute` 返回退出码 `3`、结果 `rejected`。此结果说明该测试包未通过本次分发策略评估，不代表已完成 Developer ID 签名或 Apple 公证。

## Intel x86_64

- 生成 `Super-SAG_0.1.0_x64.dmg`，大小 `18084097` 字节，SHA-256：`dcd796296caf089aa803580d669ff21388797cb38365fcd9d43af520da794731`。本机取回后摘要校验通过，并确认存在 UDIF `koly` 尾部标识。
- [Intel 测试工件](https://github.com/CalmBuilder/Super-SAG/actions/runs/42969687261/artifacts/13833518399)需登录 GitHub 并具有仓库读取权限，有效期至 2026-11-18 14:27:25（北京时间）。
- macOS 15.7.9 虚拟机完成包内容、架构、版本、签名完整性、从 DMG 复制并启动应用和隔离服务、随包 CLI 与真实临时文件检查。另从保存的同一个 DMG 执行[主程序窗口检查 42972741997](https://github.com/CalmBuilder/Super-SAG/actions/runs/42972741997)，确认屏幕上有窗口且辅助功能 `AXRaise` 可执行；该检查不覆盖窗口里的业务操作。
- 应用使用 ad-hoc 临时签名，`TeamIdentifier` 未设置；上述窗口检查中 `spctl --assess --type execute` 返回退出码 `3`、结果 `rejected`。此结果不代表已完成 Developer ID 签名或 Apple 公证。

## 范围限制

两种芯片的测试以 GitHub 托管 macOS 虚拟机和隔离数据为准；不代表物理设备、Finder 的完整安装交互、真实模型和 Agent、全部业务、旧数据升级、Safari 扩展实际启用或正式签名公证已经验收。构建未提供经校验的 Safari 扩展安装包，桌面应用中该扩展导出不可用。

两个 DMG 保存在本机被忽略目录 `.cache/macos-test-packages/0.1.0-33967c5/`，不会提交。临时验证分支的完整 Git 历史已保存在同目录 `test-workflows.bundle` 并通过 `git bundle verify`，SHA-256 为 `84cea45c0b839b7cefff47f2a19bf679cd4316de1d5c28ff3f735a94c390cdcb`；窗口验证脚本 `scripts/smoke-macos.py` 在验证提交中的 SHA-256 为 `68397e8fa6917e3474f41b393d5cc3ede4b7d68035904be9c1e50f49f4151b93`。
