# Windows 用户验收与 Web 对照基准

日期：2026-11-11。用户反馈其 Windows 环境中 **全部业务及保留数据升级已通过测试**。这是用户实机反馈，不是本机 Linux、模拟模型或 CI 代替的结果。

- 用户提供的源码提交：`9459f4b90617a2042d20848eea6560e0d6812ebe`。
- 用户提供的验收安装包 SHA-256：`F6B96076EA23BFC9C537C3D3B2B245A5D296EABDFC243FF588ED816BB2A7A644`；路径来自用户 Windows 目录 `D:\myworks\Super-SAG\src-tauri\target\release\bundle\nsis` 下的匹配安装包。
- 这是用户本机构建并验收的安装包摘要，不能未经比对就声称与 GitHub Release 下载文件或其他机器构建的安装包相同。
- 本次工作树起点 `87e133b978f6534bdca07f2ad8ac44eadc7a1101` 与上述 Windows 源码在 `src/`、`src-tauri/`、`assets/branding/`、`core/`、`client/`、`protocol/`、`cli/` 下没有差异。两者之间的浏览器扩展差异为 Safari 引导及其说明；不能据此声称所有仓库文件完全相同。
- Windows 版本、DPI、窗口尺寸、主题、语言、测试样本及逐项操作明细尚未由用户提供；后续界面逐项对照时记录实际参数和结果，不用缺失的细节否认用户的通过反馈，也不凭空补写。

该基准用于启动 Web 界面与交互对照。当前没有正式 Web 服务；旧预览只产生虚构结果，不能用于证明业务实现或浏览器对照已经通过。
