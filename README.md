# auto-download-py

`auto-download-py` 是一个面向 Windows 的 Python 混合自动化服务，核心能力包括浏览器自动化、桌面窗口自动化、屏幕/图像点击，以及供本地 Python 代码直接调用的 service 层。

当前项目不是 Vue + Java 后端结构：仓库中没有 Vue 页面，也没有 Java 的 controller、service、mapper/xml。后端主体是 FastAPI，未来前端或 Chrome 扩展应通过 HTTP API 调用 FastAPI；本地 Python 业务代码则直接 import `app.services.*`。

## 文档索引

| 文档 | 说明 |
| --- | --- |
| [架构说明](docs/architecture.md) | 项目分层、模块职责、调用链路、数据模型 |
| [关键类与函数说明](docs/key-classes-functions.md) | 核心类、函数、API 端点详细参考 |
| [依赖关系](docs/dependency-graph.md) | 外部/内部依赖、数据流、线程模型 |
| [API 调用链](docs/api-call-chain.md) | 接口到 schema、service、manager、数据库/外部依赖的映射 |
| [开发指南](docs/development-guide.md) | 新增能力时的固定改动顺序和约束 |
| [AGENT.md](AGENT.md) | 给维护者或自动化代理使用的项目规则 |
| [skills/README.md](skills/README.md) | 按能力拆分的维护说明 |

## 目录结构

```text
app/
  api/
    browser.py          # 浏览器 HTTP API，FastAPI router
    desktop.py          # 桌面/屏幕 HTTP API，FastAPI router
    health.py           # 健康检查
  browser/
    manager.py          # Playwright + CDP 浏览器运行时与会话管理
  desktop/
    windows_manager.py  # pywinauto 窗口枚举与激活
  visual/
    screen_manager.py   # pyautogui + 图像查找点击 + OCR 预留
  core/
    config.py           # .env 配置
    logging_config.py   # 日志配置
  db/
    base.py
    session.py          # SQLAlchemy engine / SessionLocal
  models/
    browser_window.py   # ad_browser_window ORM
    browser_page.py     # ad_browser_page ORM
  schemas/
    browser.py
    desktop.py
    common.py
  services/
    browser_service.py  # 本地浏览器 service
    desktop_service.py  # 本地桌面 service
    visual_service.py   # 本地图像/屏幕 service
scripts/
  demo_browser.py
  demo_desktop.py
  demo_hybrid.py
  local_service_demo.py
  smoke_test.py
browser-extension/
  README.md             # 未来 Chrome 扩展预留目录，不是当前 Vue 前端
sql/
  auto_download.sql     # MySQL 初始化脚本
docs/
  architecture.md
  api-call-chain.md
  development-guide.md
```

## 当前调用链

### 浏览器 HTTP 链路

```text
外部调用方 / 未来前端
  -> app/api/browser.py
  -> app/services/browser_service.py
  -> app/browser/manager.py
  -> Playwright + CDP
  -> SQLAlchemy
  -> ad_browser_window / ad_browser_page
```

浏览器 API 层是 `async` FastAPI router，实际同步 Playwright 能力通过 `run_in_threadpool()` 转调 service。`BrowserService` 内部使用单线程 `ThreadPoolExecutor`，并为每次 manager 调用创建和关闭 `SessionLocal()`。

### 桌面窗口链路

```text
外部调用方 / 未来前端
  -> app/api/desktop.py
  -> app/services/desktop_service.py
  -> app/desktop/windows_manager.py
  -> pywinauto
```

### 图像/屏幕链路

```text
外部调用方 / 未来前端
  -> app/api/desktop.py
  -> app/services/visual_service.py
  -> app/visual/screen_manager.py
  -> pyautogui / OpenCV / Pillow
```

### 本地 Python 链路

```text
本地业务脚本 / scripts/*.py
  -> app/services/*_service.py
  -> manager/runtime 层
```

本地调用不经过 `app/api/*`。业务代码不要直接 import API 层，也不要直接管理 `SessionLocal()`。

## 与 Vue / Java 常见结构的对照

| 常见 Vue + Java 概念 | 当前项目对应关系 |
| --- | --- |
| Vue 页面 | 当前不存在；`browser-extension/` 只是 Chrome 扩展预留目录 |
| api 文件 | 未来前端可封装对 `/auto-download/**` 的 HTTP 调用 |
| controller | `app/api/*.py` FastAPI router |
| service | `app/services/*.py` |
| manager / adapter | `app/browser/manager.py`、`app/desktop/windows_manager.py`、`app/visual/screen_manager.py` |
| mapper/xml | 当前没有；使用 SQLAlchemy model + `sql/auto_download.sql` |
| 数据库表 | `ad_browser_window`、`ad_browser_page` |

## 快速启动

### 1. 创建虚拟环境

```bash
uv venv
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

Windows CMD：

```bat
.venv\Scripts\activate.bat
```

### 2. 安装依赖

```bash
uv sync
```

### 3. 安装 Playwright 浏览器支持

```bash
uv run playwright install chrome
```

### 4. 准备配置

```bat
copy .env.example .env
```

重点检查：

- `APP_CONTEXT_PATH`：默认 `/auto-download`
- `APP_PORT`：默认 `7982`
- `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD`
- `BROWSER_EXECUTABLE_PATH`
- `PROFILE_DIR`
- `DEBUG_PORT`

Chrome 扩展工具栏注意事项：

- `BROWSER_EXECUTABLE_PATH` 推荐指向正常安装版 Chrome，例如 `C:/Program Files/Google/Chrome/Application/chrome.exe`。
- 如果继续使用 Chrome for Testing，扩展 options 页面和 service worker 可能正常，但右上角扩展工具栏菜单仍需要手动验收。
- `PROFILE_DIR` 必须指向已经安装目标扩展的 Chrome profile；启动服务前不要让其他 Chrome 进程占用同一个 profile。

### 5. 初始化数据库

```sql
source sql/auto_download.sql;
```

当前数据库表：

- `ad_browser_window`：浏览器窗口记录。
- `ad_browser_page`：窗口内页面记录。

桌面窗口和图像点击能力当前不落库。

### 6. 启动服务

开发模式：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 7982 --reload
```

或：

```bat
scripts\run_dev.bat
```

生产/普通模式：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 7982
```

或：

```bat
scripts\run_prod.bat
```

## HTTP API 总览

所有路径默认带 `APP_CONTEXT_PATH=/auto-download` 前缀。示例中的完整路径为 `/auto-download/...`。

### 健康检查

```http
GET /auto-download/health
```

### 浏览器 API

```http
POST /auto-download/browser/session/open
POST /auto-download/browser/window/open
GET  /auto-download/browser/windows
POST /auto-download/browser/tab/open?windowId=window-1
POST /auto-download/browser/page/open-url?windowId=window-1
POST /auto-download/browser/page/batch-open-config?windowId=window-1
GET  /auto-download/browser/pages?windowId=window-1
GET  /auto-download/browser/page-info?windowId=window-1&pageId=page-1
POST /auto-download/browser/page/activate?windowId=window-1&pageId=page-1
POST /auto-download/browser/page/close?windowId=window-1&pageId=page-1
POST /auto-download/browser/bing-huya?windowId=window-1
GET  /auto-download/browser/takeover/page-info?windowId=window-1
POST /auto-download/browser/window/reopen?windowId=window-1
POST /auto-download/browser/window/invalidate?windowId=window-1
POST /auto-download/browser/close?windowId=window-1
```

兼容参数：部分浏览器接口同时接受 `sessionId`，内部会解析为 `windowId`。

### 桌面和屏幕 API

```http
GET  /auto-download/desktop/windows?backend=uia&onlyVisible=true&limit=50
POST /auto-download/desktop/window/activate
POST /auto-download/desktop/click/pos
POST /auto-download/desktop/click/image
POST /auto-download/desktop/click/ocr-text
POST /auto-download/desktop/keyboard/type
POST /auto-download/desktop/keyboard/hotkey
```

## 本地 service 调用示例

### 浏览器 service

```python
from app.schemas.browser import NewTabRequest
from app.services.browser_service import browser_service

opened = browser_service.open_browser()
window_id = opened.windowId
page = browser_service.new_tab(window_id, NewTabRequest(url='https://www.bing.com'))
print(page)
```

### 桌面 service

```python
from app.schemas.desktop import WindowQueryRequest
from app.services.desktop_service import desktop_service

windows = desktop_service.list_windows(WindowQueryRequest(titleContains='Chrome'))
print(windows)
```

### 图像/屏幕 service

```python
from app.schemas.desktop import ClickPositionRequest
from app.services.visual_service import visual_service

visual_service.click_position(ClickPositionRequest(x=500, y=300))
```

## 示例脚本

```bash
uv run python scripts/local_service_demo.py
uv run python scripts/demo_browser.py
uv run python scripts/demo_desktop.py
uv run python scripts/demo_hybrid.py
uv run python scripts/smoke_test.py
```

## Batch open configured pages

Configured browser pages are stored in `ad_browser_page_config`. A single `config_code` can map to multiple URLs. Only rows with `status='1'` are opened, ordered by `sort_no,id`.

```http
POST /auto-download/browser/page/batch-open-config?windowId=window-1
Content-Type: application/json

{
  "configCode": "daily-pages",
  "bringToFront": true
}
```

The response uses the common `Result` wrapper and returns `BatchOpenPagesResponse`, including `windowId`, `configCode`, `total`, and `openedPages`.

## 开发约束

- API 层只做参数接收、schema 绑定、线程池转调和统一响应封装。
- 业务代码优先调用 `app/services/*.py`，不要直接调用 `app/api/*.py`。
- 浏览器核心逻辑放在 `app/browser/manager.py`。
- 桌面窗口逻辑放在 `app/desktop/windows_manager.py`。
- 坐标、模板图、OCR 预留逻辑放在 `app/visual/screen_manager.py`。
- 数据库持久化当前只属于浏览器窗口和页面运行状态。

更详细的新增能力规则见 [开发指南](docs/development-guide.md)。
