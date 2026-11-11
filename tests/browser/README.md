# 桌面与浏览器测试

新的 B/S 界面开发、Chrome/Edge/Safari 回归和原生窗口检查见 [`tests/bs/README.md`](../bs/README.md)。这些界面测试使用独立虚构数据，不代表真实 Web 业务验收。

原先的 `tests/visual/` Web 预研入口已停用；`reference_visual.py`、`web_workspace_visual.py` 和 `audit_preview.py` 依赖该历史入口，保留为历史记录，不用于新 Web 的实现或验收。旧测试数据文件仍供下面的既有桌面品牌测试使用，不进入新的浏览器产品入口。

## 桌面品牌界面回归

在仓库根目录安装前端依赖，并在隔离 Python 环境中安装 `tests/browser/requirements.txt` 和 Playwright Chromium，然后运行：

```bash
python tests/browser/windows_brand.py
python tests/browser/brand_completion.py
npm run build:clipper
python tests/browser/clipper_brand.py
```

`windows_brand.py` 使用虚构 Tauri 响应检查桌面前端的中英文、视口、主题、首次引导及品牌；`brand_completion.py` 检查目录显示、剪藏说明、CLI/Skill 命令和关于页，并可用 `--docs` 生成脱敏文档截图；`clipper_brand.py` 在隔离浏览器文件系统中测试扩展。它们不代替真实 Windows 原生安装和业务验收。
