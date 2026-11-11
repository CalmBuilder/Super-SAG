# 12 桌面能力与 Web 适配盘点

状态：P0 初步静态盘点，源码提交 `87e133b`。本文用于制定适配与验收范围；代码中存在的功能不等于已完成 Windows 实机或 Web 验收。各项状态在取得对应安装包、测试数据和操作证据后更新。

## 界面与交互范围

| 范围 | 主要桌面实现 | 需要对照的界面、状态与操作 | 状态 |
| --- | --- | --- | --- |
| 框架 | `src/App.svelte`、`src/components/Tree.svelte`、`src/components/DesktopWindowControls.svelte` | 左侧品牌及目录树、顶部问答/搜索/文件切换、主题、中英文、窗口控制、弹窗和导航焦点。浏览器窗口与系统托盘须单独设计。 | 静态识别；Windows 对照及 Web 待验收 |
| 问答 | `src/App.svelte`、`ConversationSidebar.svelte`、`CitationDocument.svelte`、`ToolCall.svelte`、`AnswerProcess.svelte` | 空状态、范围/模型、文件引用、历史会话、编辑、流式回答、思考过程、工具、确认、停止、错误、来源和原文返回。 | 静态识别；待验收 |
| 搜索 | `src/App.svelte`、`SearchResultItem.svelte`、`SearchSummary.svelte`、`SearchPassagePicker.svelte` | 快速/深入、范围、输入、历史、结果、分页、摘要、原文高亮和定位、返回及错误。 | 静态识别；待验收 |
| 文件和知识库 | `LibraryWorkspace.svelte`、`MarkdownReader.svelte`、`RichEditor.svelte`、`DocumentFold.svelte`、`ExploreView.svelte` | 目录层级、统计、列表和过滤、原文、编辑/新建、草稿、笔记、折叠、知识探索及来源、空/大量内容和冲突。 | 静态识别；待验收 |
| 添加与管理目录 | `FolderPicker.svelte`、`FolderIndexSettings.svelte`、`RemovedDirectories.svelte` | 文件夹多选、返回上级、隐藏项、索引选项、已移除目录、失败及恢复；Web 选择服务器授权目录。 | 静态识别；待验收 |
| 索引 | `IndexDetails.svelte`、`IndexSettings.svelte`、`IndexHistoryEntry.svelte`、`DoclingDownload.svelte` | 状态、进度、历史、暂停/恢复、格式转换组件、下载及失败处理。 | 静态识别；待验收 |
| 设置与入口 | `Settings.svelte`、`CliSettings.svelte`、`WebClipper.svelte`、`QuickSearchSettings.svelte`、`McpSettings.svelte` | 通用、外观、文件、剪藏、快捷键、模型、问答、搜索、CLI、数据隐私、关于；保存/取消、错误、密钥与工具配置。 | 静态识别；待验收 |

## 桌面调用的适配分类

前端业务调用目前通过 `src/lib/api.ts` 进入 Tauri，也有组件直接调用 Tauri 事件、窗口和更新 Channel。静态扫描到至少 70 个字面量 API 名称；`add_root_with_options`、`install_docling_profiles` 等还存在动态选择，不能把字面量计数当成完整清单。桌面命令注册表见 `src-tauri/src/lib.rs` 的 `generate_handler!`，实现 Web 前还要逐项核对参数、返回、事件及错误。

| 业务类别 | 代表性桌面命令 | Web 适配原则 |
| --- | --- | --- |
| 目录与原文 | `browse_folders`、`list_roots`、`add_root_with_options`、`remove_root`、`list_entries`、`read_document` | 服务端显式接口和授权根目录校验；目录为 Linux 服务器路径，移除保留原件。 |
| 索引 | `get_index_status`、`set_index_paused`、`reindex_all`、`get_index_history`、`install_docling_profiles` | 复用核心索引与进度能力，服务端处理文件边界和组件生命周期。 |
| 搜索及问答 | `run_query`、`summarize_search`、`cancel_query`、`resolve_tool_approval` | 区分请求、事件、任务归属、停止及工具确认；不得直接暴露通用内部命令。 |
| 文件、笔记和草稿 | `save_document`、`put_draft`、`save_note`、`verify_notes`、`load_image` | 服务端检查读写范围、目标与版本，浏览器显示真实保存及冲突结果。 |
| 历史和设置 | `list_conversations`、`edit_conversation`、`get_settings`、`save_settings`、`test_model`、`test_mcp` | 复用现有业务语义；配置和密钥应防止泄露，后续按用户与租户隔离。 |
| 知识探索 | `explore_overview`、`explore_graph`、`explore_neighbors`、`explore_evidence` | 逐项核对实际入口和核心支持，图、证据及任务取消均不可遗漏。 |
| 原生窗口与系统能力 | `show_quick_search`、`reveal_path`、`open_data_directory`、`quit_application` | 不能把 Windows 本机路径或窗口命令暴露给浏览器；列出可行等效方式并确认。 |
| 更新、剪藏和 Agent 接入 | `check_app_update`、`export_web_clipper`、`get_cli_settings`、`install_cli_integration` | 区分桌面包、浏览器与 Linux 服务端；Web Agent 在服务器运行，不要求用户电脑安装 Agent。 |

## 事件和平台边界

- 桌面前端直接订阅 `index-progress`、`data-changed`、`settings-changed`、`history-changed`、`query-progress`、`tool-approval`、`document-fold-progress`、`app-error` 等事件；快捷搜索与退出还使用原生窗口事件。适配需同时覆盖订阅、取消订阅、任务对应、错误与组件销毁，不能只替换请求函数。
- 本机核心服务将部分事件按连接归属，广播队列拥塞时可跳过事件并触发刷新；浏览器断开、服务重启及慢消费者如何恢复必须另行设计和测试，不能假定现有服务提供完整重放或多用户隔离。
- 既有预览使用虚构 Tauri 响应，`src/App.svelte` 等共享文件也包含预览专用的 Web 分支；应先区分桌面本来需要的代码与预览逻辑。正式实现从桌面能力出发新增适配，不直接搬用预览壳层、替身或旧 Web 业务。
- 浏览器关闭页面不等于停止服务器；本地快捷搜索、剪贴板、资源管理器、下载与后台任务的行为需与用户确认。Web 用户仅使用浏览器；实际知识目录、业务服务及 Agent 在 Linux 服务器。

## 基准与下一步

1. 为每个界面项目记录 Windows 安装包、源码、截图、分辨率、DPI、主题、语言、文件样例和实际操作结果；已有的单张启动截图不能代表上述全部功能通过。
2. 按视觉方案制作隔离测试资料，并建立桌面/Web 适配清单；完成桌面命令及事件的参数、失败场景和权限边界映射。
3. 建立真实 Chrome、Edge、Safari 的可用测试环境；Safari 需在 macOS 中实测浏览器交互，不能用 WebKit 构建冒充。然后按 [V1–V4](11-Linux-Web详细实施方案.md#分阶段工作与出口) 逐项开始界面实现。
