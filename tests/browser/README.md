# 真实浏览器基线检查

`reference_visual.py` 用真实 Chromium 渲染当前桌面 Svelte 页面，桌面的 Tauri 接口、文件和模型均是测试替身。它仅用于留存视觉基线与检查导航、添加文件夹弹窗和设置布局，**不是 Web 产品、真实业务、Windows 原生安装或完整一致性验收**。截图只包含虚构数据，默认写入 Git 忽略的 `.cache/visual-baseline/`。

也可在本机打开带提示的开发样式预览：

```bash
npx vite --host 127.0.0.1 --port 1427 --strictPort
```

使用独立浏览器 profile 访问 `http://127.0.0.1:1427/tests/visual/`。此预览直接复用桌面组件、只允许回环访问，内容是虚构数据；不支持真实文件读写、索引或问答。桌面共享界面的 Super-SAG 品牌已接入，Windows 安装包和原生行为仍待实机验收。预览目前会改写同源的部分 `sag.*` 本地存储，不能与真实状态共用 origin；窄屏侧栏文件夹菜单还存在遮挡和切换后抽屉未关闭问题。它与未来的 Web 服务和 `app.sh` 无关，不能用于生产或对外提供访问。

在项目根目录运行：

```bash
npm ci
python3 -m venv /tmp/super-sag-browser
/tmp/super-sag-browser/bin/pip install -r tests/browser/requirements.txt
/tmp/super-sag-browser/bin/python -m playwright install chromium
/tmp/super-sag-browser/bin/python tests/browser/reference_visual.py
```

测试只监听临时回环端口，结束时关闭自己启动的 Vite 进程，不修改 `pros/SAG-Wiki` 或任何用户数据。可用 `SAG_VISUAL_EVIDENCE_DIR` 指定其他截图和结果目录；测试应始终在工作树运行，不在只读参考目录安装依赖或构建。

## 桌面品牌界面回归

```bash
/tmp/super-sag-browser/bin/python tests/browser/windows_brand.py
```

该脚本以桌面前端入口和虚构 Tauri 响应检查中英文、三种视口、主题、首次引导、品牌和禁用的更新入口，默认写入 `.cache/desktop-brand/`。可用 `SAG_DESKTOP_BRAND_EVIDENCE_DIR` 指定其他结果目录。该检查不是 Windows 原生或业务验收。

## Web 公共工作区视觉回归

```bash
/tmp/super-sag-browser/bin/python tests/browser/web_workspace_visual.py
```

该脚本使用独立的只读参考入口 `reference.html` 从 `pros/SAG-Wiki` 加载固定桌面组件，另行启动当前桌面和测试预览，在相同夹具及视口下比较布局。脚本覆盖桌面与窄屏导航、侧栏键盘操作、空目录、长名称、添加失败和启动失败；还使用只读虚构会话检查回答、引用、文档返回、长会话、会话搜索、消息编辑和原文读取失败；模拟流式片段、停止、迟到事件、失败和重试，以及虚构工具状态和确认弹窗；使用预设结果检查搜索列表、原文、分页和空结果；检查虚构多层目录、编辑器、新建文档的保存位置、长文件名、读取及保存失败；检查文件夹多选与索引选项、设置分类和主题；截图和机器可读结果默认写入 `.cache/web-workspace/`，可用 `SAG_WEB_VISUAL_EVIDENCE_DIR` 改到其他非参考目录。

夹具只提供虚构结果并拒绝未实现的写入。视觉回归不会启动实际 Web 后端，不证明目录、索引、问答、权限或 Windows 安装升级可用。真实 Windows 反馈和其余界面状态仍须逐项验收。

## 预览缺陷审核

```bash
/tmp/super-sag-browser/bin/python tests/browser/audit_preview.py
```

该诊断在临时 Vite 缓存、随机回环端口和独立 Chromium profile 中使用虚构数据，检查窄屏文件夹菜单、切换后抽屉状态以及已有同源本地存储是否被改写。默认结果写入 `.cache/preview-audit/`，可用 `SAG_AUDIT_EVIDENCE_DIR` 改到其他非参考目录；发现问题时以非零状态退出。当前已知问题未修复，因此当前运行返回非零是审核结果，不能记为回归通过。
