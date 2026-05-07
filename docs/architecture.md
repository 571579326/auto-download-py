# 架构说明

## 项目定位

`auto-download-py` 是一个 Python 3.11 / Windows 自动化服务。它同时支持两种入口：

- 本地 Python 代码直接调用 `app/services/*.py`。
- 外部系统、未来前端或 Chrome 扩展通过 FastAPI HTTP API 调用。

当前仓库没有 Vue 页面，也没有 Java controller/service/mapper/xml。`browser-extension/` 是未来 Chrome 扩展预留目录，不是当前前端实现。

## 分层

```text
HTTP 调用方 / 未来前端
  -> app/api/*.py
  -> app/services/*.py
  -> app/browser | app/desktop | app/visual
  -> 外部自动化库 / 数据库
```

本地 Python 调用方直接从 `app/services/*.py` 进入，不经过 HTTP API。

| 层级 | 目录 | 职责 |
| --- | --- | --- |
| API 层 | `app/api` | FastAPI router，接收参数，绑定 schema，返回 `Result` |
| service 层 | `app/services` | 本地业务调用入口，隔离 API 和核心实现 |
| 浏览器运行时 | `app/browser` | Playwright + CDP，窗口/页面运行时和持久化同步 |
| 桌面窗口 | `app/desktop` | pywinauto 窗口枚举与激活 |
| 图像/屏幕 | `app/visual` | pyautogui 坐标点击、模板图点击、OCR 预留 |
| schema | `app/schemas` | Pydantic 请求/响应模型 |
| 数据库 | `app/models`、`sql` | SQLAlchemy model 和 MySQL 初始化脚本 |

## 路由前缀

FastAPI app 在 `app/main.py` 中挂载路由：

```text
app.include_router(..., prefix=settings.app_context_path)
```

默认 `APP_CONTEXT_PATH=/auto-download`，因此接口完整路径是：

```text
/auto-download/health
/auto-download/browser/**
/auto-download/desktop/**
```

如果 `.env` 中修改 `APP_CONTEXT_PATH`，文档中的 `/auto-download` 前缀需要对应替换。

## 浏览器链路

```text
app/api/browser.py
  -> app/services/browser_service.py
  -> app/browser/manager.py
  -> Playwright Sync API + CDP
  -> SQLAlchemy SessionLocal
  -> ad_browser_window / ad_browser_page
```

浏览器 API 层是 `async`，但 Playwright 使用同步 API。API 层必须使用 `run_in_threadpool()` 调 service，避免在 asyncio event loop 中直接执行同步 Playwright 操作。

`BrowserService` 内部用单线程 `ThreadPoolExecutor(max_workers=1)` 串行执行浏览器任务。每次调用都会创建 `SessionLocal()`，交给 `BrowserSessionManager` 执行业务和数据库同步，最后关闭数据库会话。

## 桌面窗口链路

```text
app/api/desktop.py
  -> app/services/desktop_service.py
  -> app/desktop/windows_manager.py
  -> pywinauto
```

桌面能力按 Windows 设计。`type_text()` 和 `hotkey()` 使用 `pyautogui` 发送全局键盘事件，调用前应先确保目标窗口已激活。

## 图像/屏幕链路

```text
app/api/desktop.py
  -> app/services/visual_service.py
  -> app/visual/screen_manager.py
  -> pyautogui / OpenCV / Pillow
```

图像点击依赖屏幕截图与模板匹配，容易受 DPI 缩放、主题、分辨率和遮挡影响。OCR 点击当前只是预留接口，不默认安装或接入 `cnocr`。

## 数据库边界

当前只有浏览器窗口和页面状态落库：

- `ad_browser_window`：窗口业务 ID、状态、最后激活页面标题和 URL。
- `ad_browser_page`：页面标题、URL、状态、窗口内排序、失效时间。

桌面窗口、键盘输入、坐标点击、模板图点击当前不落库。后续如果要持久化这些能力，应先新增 model 和 SQL，再从对应 manager/service 明确写入边界。

## Batch page config persistence

`ad_browser_page_config` stores reusable browser page URL groups. The batch-open API reads rows by `config_code`, filters `status='1'`, orders by `sort_no,id`, and writes opened runtime pages back to `ad_browser_page`.
