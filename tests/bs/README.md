# B/S 界面测试

本目录是新浏览器入口的隔离界面测试。`fixture.ts` 是独立的测试平台，只返回虚构数据；它不注入 Tauri 全局对象、不连接真实目录或模型，也不进入 `web/index.html` 的构建。正式入口目前没有接通服务，会明确显示连接失败；不能将该阶段称为可部署 Web 产品。

先在项目根目录安装前端依赖，并在隔离 Python 环境中安装 `tests/browser/requirements.txt`。在真实浏览器中执行：

```bash
python tests/bs/browser_ui.py --browser chromium
python tests/bs/browser_ui.py --browser chrome
python tests/bs/browser_ui.py --browser msedge
```

Chrome 和 Edge 需要在运行机器上分别安装实际浏览器；Chromium 结果不能代替它们。脚本只监听随机回环端口，创建全新浏览器 profile，以虚构数据检查导航、主题、语言、空/大量目录、320/375/768/959/960 宽度、菜单与抽屉、故障/重试及正式入口禁用状态。默认结果和脱敏截图写入被忽略的 `.cache/bs-ui/`，可用 `--output` 指定目录。

macOS 实际 Safari 运行 `python tests/bs/safari_ui.py`，需要安装 Selenium 并启用 Safari 的 WebDriver；不能将 Playwright WebKit 冒充 Safari。CI 的 `bs-ui.yml` 分别运行真实 Chrome、Edge、Safari，并保存短期测试产物。云主机不是物理设备，结果只说明脚本覆盖的界面状态，不能代替已验收 Windows 安装版的实际对照或任何真实业务验收。

桌面共享代码回归使用实际安装包：macOS CI 的 `smoke-macos.py --exercise-ui` 调用 `native_ui_macos.swift`，操作真实窗口的三个工作区和设置；Windows CI 的 `native_ui_windows.ps1` 与 Python 驱动操作已安装应用的 WebView。两者都仅允许在一次性 GitHub 托管主机上使用隔离数据运行，Windows 脚本会清理临时 WebView2 调试策略。它们不覆盖真实问答、索引或物理设备。
