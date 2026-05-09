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
| [RPA公共方法层](docs/rpa-common-methods.md) | 页面/DOM/图像/鼠标/键盘/数据处理等 RPA 公共动作说明 |
| [AGENT.md](AGENT.md) | 给维护者或自动化代理使用的项目规则 |
| [skills/README.md](skills/README.md) | 按能力拆分的维护说明 |

## 目录结构

```text
app/
  api/
    browser.py          # 浏览器 HTTP API，FastAPI router
    business.py         # 业务流程 HTTP API（page-flow），FastAPI router
    desktop.py          # 桌面/屏幕 HTTP API，FastAPI router
    health.py           # 健康检查
    rpa.py              # RPA 公共方法 HTTP API，FastAPI router
  browser/
    manager.py          # Playwright + CDP 浏览器运行时与会话管理
    rpa_locator_backend.py  # RPA 网页 UI 定位器后端
  desktop/
    windows_manager.py  # pywinauto 窗口枚举与激活
  visual/
    screen_manager.py   # pyautogui + 图像查找点击 + OCR 预留
    templates/          # 图像匹配模板文件（如 cf_check_dark.png）
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
    rpa.py              # RPA 公共方法请求/响应模型
  services/
    browser_service.py              # 本地浏览器 service
    business_service.py             # 本地业务流程 service（入口）
    business_common_service.py      # 业务公共编排方法层
    business_image_click_service.py # 业务公共图像点击服务
    desktop_service.py              # 本地桌面 service
    visual_service.py               # 本地图像/屏幕 service
    rpa/                            # RPA 公共方法层（按功能分类）
      rpa_page_service.py           # 页面：重连、打开、刷新、截图等
      rpa_element_service.py        # DOM 元素：点击、输入、读文本等
      rpa_locator_service.py        # 网页 UI 定位：查找、描述、计数
      rpa_image_service.py          # 图像：查找、等待、点击
      rpa_mouse_service.py          # 鼠标：坐标点击、移动、拖拽、滚轮
      rpa_keyboard_service.py       # 键盘：输入、快捷键、组合键
      rpa_clipboard_service.py      # 剪贴板：设置、读取、粘贴
      rpa_data_service.py           # 数据处理：清洗、过滤、排序、去重等
      rpa_wait_service.py           # 等待：sleep、等元素、等图像、等URL
      rpa_assert_service.py         # 断言：URL、元素、文本、图像
      rpa_flow_service.py           # JSON 流程编排：顺序执行、重试、失败策略
  utils/
    http_utils.py       # HTTP 请求工具（get/put JSON）
    image_utils.py      # 图像点击工具函数（单图/多图/轮询）
scripts/
  check_db.py           # 数据库连接检查
  demo_browser.py
  demo_desktop.py
  demo_hybrid.py
  e2e_test.py           # E2E 端到端测试脚本
  local_service_demo.py
  run_dev.bat
  run_prod.bat
  smoke_test.py
tests/
  test_page_flow.py     # 业务流程接口与工具函数的单元测试
browser-extension/
  README.md             # 未来 Chrome 扩展预留目录，不是当前 Vue 前端
sql/
  auto_download.sql     # MySQL 初始化脚本
docs/
  architecture.md
  api-call-chain.md
  development-guide.md
  dependency-graph.md
  key-classes-functions.md
  rpa-common-methods.md
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
或（本地 Python 调用）
  -> app/utils/image_utils.py（工具函数层）
  -> app/services/visual_service.py
  -> app/visual/screen_manager.py
```

### 本地 Python 链路

```text
本地业务脚本 / scripts/*.py
  -> app/services/*_service.py
  -> manager/runtime 层
本地业务代码也可直接使用工具函数：
  -> app/utils/image_utils.py（点击工具函数）
  -> app/services/visual_service.py
  -> app/visual/screen_manager.py
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

- 当前默认按你手动验证可用的快捷方式对齐：`BROWSER_EXECUTABLE_PATH=C:/software/chrome-win64/chrome.exe`、`PROFILE_DIR=C:/chrome_debug_profile`、`DEBUG_PORT=9222`。
- `OPEN_PAGE_MODE=native` 时，项目会优先使用 Chrome 原生命令行创建窗口，避免默认走 `Target.createTarget` 或 `window.open`。
- `AUTO_CLICK_SECURITY_CHECK=false` 时，业务流程不会自动点击安全验证图片；遇到 Cloudflare 等安全验证时请手动完成，并依赖同一个 `PROFILE_DIR` 保留验证状态。
- 不要把 `PROFILE_DIR` 指向日常 Chrome 默认用户目录，例如 `C:/Users/用户名/AppData/Local/Google/Chrome/User Data`。

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
POST /auto-download/browser/session/open-pure?url=&newWindow=false
POST /auto-download/browser/session/open-selenium?url=&newWindow=true
POST /auto-download/browser/window/open
POST /auto-download/browser/window/open-pure?url=&newWindow=false
POST /auto-download/browser/window/open-selenium?url=&newWindow=true
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

### 业务流程 API

```http
POST /auto-download/biz/page-flow?configCode=acg18&clickOffsetX=14&clickOffsetY=13
POST /auto-download/biz/page-flow-selenium?configCode=acg18&clickOffsetX=14&clickOffsetY=13
```

`clickOffsetX` / `clickOffsetY` 为可选参数，相对匹配到的图片区域左上角计算的点击偏移。

### RPA 公共方法 API

```http
# 页面
POST /auto-download/rpa/page/reconnect
POST /auto-download/rpa/page/info
POST /auto-download/rpa/page/list
POST /auto-download/rpa/page/activate
POST /auto-download/rpa/page/open-tab
POST /auto-download/rpa/page/open-url
POST /auto-download/rpa/page/reload
POST /auto-download/rpa/page/wait-load-state
POST /auto-download/rpa/page/wait-url
POST /auto-download/rpa/page/screenshot

# DOM 元素
POST /auto-download/rpa/element/exists
POST /auto-download/rpa/element/click
POST /auto-download/rpa/element/input
POST /auto-download/rpa/element/text
POST /auto-download/rpa/element/attribute
POST /auto-download/rpa/element/press
POST /auto-download/rpa/element/select

# 网页 UI 定位
POST /auto-download/rpa/locator/find
POST /auto-download/rpa/locator/describe
POST /auto-download/rpa/locator/count

# 图像
POST /auto-download/rpa/image/locate
POST /auto-download/rpa/image/wait
POST /auto-download/rpa/image/click
POST /auto-download/rpa/image/click-many

# 鼠标
POST /auto-download/rpa/mouse/click
POST /auto-download/rpa/mouse/move
POST /auto-download/rpa/mouse/drag
POST /auto-download/rpa/mouse/scroll

# 键盘
POST /auto-download/rpa/keyboard/type
POST /auto-download/rpa/keyboard/hotkey
POST /auto-download/rpa/keyboard/press

# 剪贴板
POST /auto-download/rpa/clipboard/set
POST /auto-download/rpa/clipboard/get
POST /auto-download/rpa/clipboard/paste

# 数据处理
POST /auto-download/rpa/data/clean
POST /auto-download/rpa/data/filter
POST /auto-download/rpa/data/sort
POST /auto-download/rpa/data/unique
POST /auto-download/rpa/data/group-count
POST /auto-download/rpa/data/extract-regex
POST /auto-download/rpa/data/read-file
POST /auto-download/rpa/data/write-file

# 等待
POST /auto-download/rpa/wait/sleep
POST /auto-download/rpa/wait/element
POST /auto-download/rpa/wait/image
POST /auto-download/rpa/wait/url

# 断言
POST /auto-download/rpa/assert/url-contains
POST /auto-download/rpa/assert/element-exists
POST /auto-download/rpa/assert/image-exists
POST /auto-download/rpa/assert/text-contains

# 流程编排
POST /auto-download/rpa/flow/run
```

请求体和详细说明见 [docs/rpa-common-methods.md](docs/rpa-common-methods.md)。

### 图像/屏幕工具函数

除了 HTTP API 外，`app/utils/image_utils.py` 提供以下可直接 import 使用的工具函数：

| 函数 | 说明 |
|------|------|
| `click_image_until_found(image_path, ...)` | 单图轮询点击，找到并点击后返回 `ClickImageResponse` |
| `click_images_until_found(image_paths, ...)` | 多图轮询点击，支持 `or` / `and` 两种匹配模式 |
| `click_image_if_exists(image_path, ...)` | 兼容旧版：找到并点击返回 `True`，未找到返回 `False`（不抛异常） |
| `normalize_match_mode(match_mode)` | 匹配模式标准化：`or/any/或` → `or`，`and/all/和` → `and` |
| `normalize_image_paths(image_paths, image_path)` | 路径去重与标准化 |

#### click_images_until_found 示例

```python
from app.utils.image_utils import click_images_until_found

# OR 模式：任意一张出现即点击
clicked = click_images_until_found(
    image_paths=['cf_check_dark.png', 'cf_check_white.png'],
    confidence=0.7,
    timeout_ms=30000,
    match_mode='or',
)

# AND 模式：全部找到后依次点击
clicked = click_images_until_found(
    image_paths=['login_btn.png', 'confirm_btn.png'],
    match_mode='and',
)
```

#### click_image_if_exists 示例

```python
from app.utils.image_utils import click_image_if_exists

success = click_image_if_exists(
    image_path='security_check.png',
    confidence=0.8,
    timeout_ms=5000,
)
if success:
    print('已点击安全验证图像')
```

### 桌面和屏幕 API

```http
GET  /auto-download/desktop/windows?backend=uia&onlyVisible=true&limit=50
POST /auto-download/desktop/window/activate
POST /auto-download/desktop/click/pos
POST /auto-download/desktop/click/image
POST /auto-download/desktop/click/images
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

## 异常处理

`app/main.py` 注册了三个全局异常处理器：

| 异常类型 | HTTP 状态码 | 说明 |
|---------|------------|------|
| `ValueError` | 400 | 参数校验失败，如 `imagePath不存在`、`configCode 配置不存在` |
| `RuntimeError` | 500 | 运行时错误，如 `超时未找到目标图片`、浏览器启动失败 |
| `Exception` | 500 | 未预期异常兜底处理 |

业务流程 `page-flow` 接口中，图像点击失败不会导致整个流程 500 报错，而是以 `imageClicked: false` 返回，浏览器打开和页面配置正常完成。

## 测试

### 单元测试

```bash
uv run pytest tests/ -v
```

当前测试覆盖：

| 测试类 | 覆盖目标 |
|--------|---------|
| `TestPageFlowAPI` | page-flow 接口：完整流程、图像未找到、不传图像、浏览器启动失败、配置不存在、置信度参数 |
| `TestBusinessService` | BusinessService.open_pages_and_check_image 业务逻辑：全流程成功、图像未点击、无图像路径、配置错误时关闭窗口 |
| `TestClickImageIfExists` | click_image_if_exists 工具函数：点击成功/失败、错误回调处理、自定义超时/重试 |
| `TestScreenManagerClickImage` | ScreenManager.click_image：成功点击、超时、路径不存在、区域和灰度参数 |

### E2E 测试

```bash
uv run python scripts/e2e_test.py
```

注意：E2E 测试需要服务正在运行（`localhost:7982`），且 Chrome 调试端口 9222 可达。

## 开发约束

- API 层只做参数接收、schema 绑定、线程池转调和统一响应封装。
- 业务代码优先调用 `app/services/*.py`，不要直接调用 `app/api/*.py`。
- 业务编排层（`app/services/business_common_service.py`）封装可复用的多步骤业务逻辑，供 `BusinessService` 等入口 service 调用。
- RPA 公共方法层（`app/services/rpa/*.py`）按功能分类封装通用自动化动作，供业务 service 和 JSON 流程编排使用。
- 工具函数层（`app/utils/image_utils.py`）封装常用的图像点击逻辑，供业务代码直接 import。
- 浏览器核心逻辑放在 `app/browser/manager.py`。
- 桌面窗口逻辑放在 `app/desktop/windows_manager.py`。
- 坐标、模板图、OCR 预留逻辑放在 `app/visual/screen_manager.py`。
- 数据库持久化当前只属于浏览器窗口和页面运行状态。
- `scripts/e2e_test.py` 用于端到端验证，需要服务运行中执行。

更详细的新增能力规则见 [开发指南](docs/development-guide.md)。

## 本版浏览器打开与图像点击说明

本版默认使用 `OPEN_PAGE_MODE=cdp_http`：

- `/browser/session/open` 只负责启动或挂接 Chrome，不再强制等待 Playwright 获取页面标题、DOM 加载或 iframe 加载。
- `/browser/page/batch-open-config` 在 `cdp_http` 模式下通过 Chrome DevTools HTTP `/json/new` 请求打开页面，只要 Chrome 接收打开请求就继续后续流程。
- 这样可以避免旧版 `native` 模式反复执行 `chrome.exe --new-window` 后，页面肉眼已打开但 Playwright 没识别到新 Page，导致接口卡死或 500。

自动点击安全验证图像默认配置为：

```properties
AUTO_CLICK_SECURITY_CHECK=true
AUTO_CLICK_IMAGE_PATHS=C:/code/py/auto-download-py/app/visual/templates/cf_check_dark.png;C:/code/py/auto-download-py/app/visual/templates/cf_check_white.png
AUTO_CLICK_IMAGE_MATCH_MODE=or
```

即 `cf_check_dark.png` 和 `cf_check_white.png` 是“或”关系，只要屏幕上出现任意一个，就点击出现的那一个。

也可以通过接口手动测试多图点击：

```http
POST /auto-download/desktop/click/images
Content-Type: application/json

{
  "imagePaths": [
    "C:/code/py/auto-download-py/app/visual/templates/cf_check_dark.png",
    "C:/code/py/auto-download-py/app/visual/templates/cf_check_white.png"
  ],
  "matchMode": "or",
  "confidence": 0.7,
  "timeoutMs": 30000,
  "retryIntervalMs": 400
}
```

图像匹配支持两种模式：

| 模式 | 说明 |
|------|------|
| `or` | 任一模板匹配成功即点击该位置（默认） |
| `and` | 所有模板均匹配成功后才依次点击每个位置 |

### 点击偏移（Click Offset）

图像自动点击支持点击坐标微调，适用于模板图像本身的注册/登录按钮位置与目标点击点存在固定偏移的场景。

配置方式（全局生效）：

```properties
AUTO_CLICK_IMAGE_CLICK_OFFSET_X=14
AUTO_CLICK_IMAGE_CLICK_OFFSET_Y=13
```

也可以在 API 请求中按次指定：

```http
POST /auto-download/biz/page-flow?configCode=acg18&clickOffsetX=14&clickOffsetY=13
```

偏移值会叠加到图像匹配中心坐标上，最终点击位置为 `(matchCenterX + offsetX, matchCenterY + offsetY)`。

### DPI 感知

`POST /desktop/click/image` 和 `POST /desktop/click/images` 接口会自动启用进程 DPI 感知。启用后截取的屏幕坐标和鼠标点击使用物理像素坐标，确保与模板图的匹配一致性。

### 点击前激活窗口

`POST /desktop/click/image` 和 `POST /desktop/click/images` 接口默认会在点击前自动激活目标窗口，确保点击事件能正确送达。由以下配置控制：

```properties
AUTO_CLICK_ACTIVATE_WINDOW_BEFORE=true
```

## 纯净模式打开浏览器接口

保留原接口：

```http
POST /auto-download/browser/session/open
```

新增纯净模式接口：

```http
POST /auto-download/browser/session/open-pure
```

别名：

```http
POST /auto-download/browser/window/open-pure
```

纯净模式只执行与手动快捷方式尽量一致的 Chrome 启动命令：

```text
chrome.exe --remote-debugging-port=9222 --user-data-dir=C:/chrome_debug_profile
```

它不会执行以下动作：

- 不调用 `playwright.chromium.connect_over_cdp`；
- 不调用 Chrome DevTools HTTP `/json/new`；
- 不读取 `context.pages`、`page.title()`、`iframe`、target diagnostics；
- 不进入 browser-service 单线程队列；
- 不等待页面加载完成。

可选参数：

```http
POST /auto-download/browser/session/open-pure?url=https://hxcy.top/&newWindow=false
```

`newWindow` 默认是 `false`，用于尽量减少和手动快捷方式之间的差异。


## Selenium 附加模式打开窗口接口

新增 Selenium 短接管打开接口：

```http
POST /auto-download/browser/session/open-selenium?url=https://hxcy.top/&newWindow=true
```

别名：

```http
POST /auto-download/browser/window/open-selenium?url=https://hxcy.top/&newWindow=true
```

该接口流程：

1. 如果 `127.0.0.1:DEBUG_PORT` 没有 Chrome 调试端口，先用纯净模式启动 Chrome。
2. 使用 Selenium `debuggerAddress=127.0.0.1:DEBUG_PORT` 附加到这个已经运行的 chromeTest/Chrome。
3. 根据 `newWindow` 决定是否通过 Selenium 新开窗口。
4. 使用 `window.location.href` 发起 URL 跳转，避免 `driver.get()` 在 Cloudflare/iframe 页面长期阻塞。
5. 调用 `driver.quit()` 断开 Selenium，不保存全局 driver。

配置项：

```properties
SELENIUM_BROWSER_START_URL=about:blank
SELENIUM_BROWSER_NEW_WINDOW=true
SELENIUM_PAGE_LOAD_TIMEOUT_MS=8000
SELENIUM_CHROMEDRIVER_PATH=
```

通常不需要手动配置 `SELENIUM_CHROMEDRIVER_PATH`，Selenium Manager 会自动处理；公司网络或离线环境失败时再填写本机 `chromedriver.exe` 路径。

## page-flow 短接管版本

当前保留两套业务流程接口：

```http
POST /auto-download/biz/page-flow?configCode=acg18
```

该接口现在是 **Playwright 短接管版**：不再先调用 `/browser/session/open` 建立长期 Playwright runtime，而是只在打开配置页时临时 `connect_over_cdp`，发起 URL 跳转后立即断开。默认不读取 `title/url`，不等待 DOM、iframe 或 load。

```http
POST /auto-download/biz/page-flow-selenium?configCode=acg18
```

该接口是 **Selenium 短接管复现版**：先确保 Chrome/chromeTest 以 `--remote-debugging-port=9222 --user-data-dir=C:/chrome_debug_profile` 方式运行，再通过 Selenium `debuggerAddress=127.0.0.1:9222` 短暂附加，打开配置页后立即 `driver.quit()` 断开，随后再执行桌面图像识别点击。

推荐测试顺序：

1. 先用 `/browser/session/open-selenium?url=https://hxcy.top/&newWindow=true` 验证 Selenium 附加打开方式可用。
2. 再调用 `/biz/page-flow-selenium?configCode=acg18` 验证完整业务流程。
3. 最后调用 `/biz/page-flow?configCode=acg18` 验证 Playwright 短接管版。

相关配置：

```properties
SELENIUM_READ_PAGE_INFO=false
PLAYWRIGHT_ONCE_NEW_WINDOW=true
PLAYWRIGHT_ONCE_CONNECT_TIMEOUT_MS=5000
PLAYWRIGHT_ONCE_NAVIGATION_TIMEOUT_MS=3000
PLAYWRIGHT_ONCE_READ_PAGE_INFO=false
```

`false` 表示打开 URL 后不额外读取页面标题、当前 URL，也不等待页面加载完成，用来降低自动化接管强度。


## 业务公共编排层

新增 `app/services/business_common_service.py`，用于封装跨步骤的公共业务逻辑。通过将多步操作（如：打开页面 → 等待加载 → 点击图像 → 获取结果）组合为可复用的编排方法，简化 `BusinessService` 的调用链路。

典型场景示例：

```python
# 重构前：BusinessService 内直接处理所有步骤
steps = [step1, step2, step3]
for step in steps:
    ...

# 重构后：通过 BusinessCommonService 一键编排
from app.services.business_common_service import business_common_service
result = business_common_service.open_page_and_auto_click(
    window_id=window_id,
    config_code="acg18",
    wait_before_click=3.0,
)
```


## RPA 公共方法层

本项目已新增 `app/services/rpa/` 模块和 `/rpa/**` HTTP API，提供按功能分类的通用自动化动作。所有 RPA 动作均支持 **HTTP 调用** 和 **本地 Python import** 两种使用方式。

### 分层架构

```
HTTP API 层（app/api/rpa.py）
    ↓
Service 层（app/services/rpa/*.py）
    ├── rpa_page_service.py      # 页面管理（重连、打开、刷新、截图等）
    ├── rpa_element_service.py    # DOM 元素操作（点击、输入、读文本等）
    ├── rpa_locator_service.py    # 网页 UI 定位（查找、描述、计数）
    ├── rpa_image_service.py      # 图像查找/等待/点击
    ├── rpa_mouse_service.py      # 鼠标动作（坐标点击、移动、拖拽、滚轮）
    ├── rpa_keyboard_service.py   # 键盘输入（文本、快捷键、组合键）
    ├── rpa_clipboard_service.py  # 剪贴板操作（设置、读取、粘贴）
    ├── rpa_data_service.py       # 数据处理（清洗、过滤、排序、去重等）
    ├── rpa_wait_service.py       # 等待（sleep、等元素、等图像、等URL）
    ├── rpa_assert_service.py     # 断言（URL、元素、文本、图像）
    └── rpa_flow_service.py       # JSON 流程编排（顺序执行、重试、失败策略）
    ↓
Browser Manager（app/browser/manager.py） / Screen Manager（app/visual/screen_manager.py）
```

### RPA 调用示例

```python
from app.services.rpa.rpa_page_service import rpa_page_service
from app.services.rpa.rpa_element_service import rpa_element_service

# 重连已有页面
page = await rpa_page_service.rpa_reconnect_page(window_id="window-1")

# 打开新页面
page = await rpa_page_service.rpa_open_url(window_id="window-1", url="https://example.com")

# 查找并点击元素
from app.schemas.rpa import RPALocator
locator = RPALocator(by="css", value="#login-btn")
await rpa_element_service.rpa_element_click(window_id="window-1", locator=locator)
```

完整功能说明和请求体格式见 [docs/rpa-common-methods.md](docs/rpa-common-methods.md)。
