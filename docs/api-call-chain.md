# API 调用链

默认接口前缀为 `/auto-download`，由 `.env` 中的 `APP_CONTEXT_PATH` 控制。如需修改，所有文档中的路径需对应替换。

## 统一响应格式

所有接口返回统一的 `Result[T]` 结构：

```json
{
    "code": 200,
    "message": "success",
    "data": { ... }
}
```

### 通用状态码

| HTTP 状态码 | Result code | 说明 |
| --- | --- | --- |
| 200 | 200 | 成功 |
| 400 | 400 | 参数校验失败 / 业务逻辑异常（`ValueError`） |
| 500 | 500 | 运行时错误 / 未捕获异常 |

---

## 健康检查

| 接口 | API 函数 | service / manager | 说明 |
| --- | --- | --- | --- |
| `GET /auto-download/health` | `health.py::health` | 无 | 返回服务健康状态 |

**成功响应**: `{"code": 200, "message": "ok", "data": {}}`

---

## 浏览器 API

所有浏览器接口需要 `windowId` 或兼容参数 `sessionId`。API 层通过 `_resolve_window_id()` 解析，解析失败返回 `ValueError('windowId不能为空')`。

| 接口 | 请求/响应 schema | service | manager | 外部依赖/数据库 |
| --- | --- | --- | --- | --- |
| `POST /auto-download/browser/session/open` | `OpenWindowResponse` | `browser_service.open_browser()` | `open_window()` | Playwright/CDP，`ad_browser_window` |
| `POST /auto-download/browser/window/open` | `OpenWindowResponse` | `browser_service.open_browser()` | `open_window()` | 同上，兼容窗口命名 |
| `GET /auto-download/browser/windows` | `WindowListResponse` | `browser_service.list_windows()` | `list_windows()` | `ad_browser_window` |
| `POST /auto-download/browser/tab/open` | `NewTabRequest` / `PageInfoResponse` | `browser_service.new_tab()` | `new_tab()` | Playwright page，`ad_browser_page` |
| `POST /auto-download/browser/page/open-url` | `OpenUrlRequest` / `PageInfoResponse` | `browser_service.open_url()` | `open_url()` | Playwright page，`ad_browser_page` |
| `POST /auto-download/browser/page/batch-open-config` | `OpenConfiguredPagesRequest` / `BatchOpenPagesResponse` | `browser_service.open_config_pages()` | `open_config_pages()` | `ad_browser_page_config` + Playwright + `ad_browser_page` |
| `GET /auto-download/browser/pages` | `PageListResponse` | `browser_service.list_pages()` | `list_pages()` | `ad_browser_page` + runtime page |
| `GET /auto-download/browser/page-info` | `PageInfoResponse` | `browser_service.get_page_info()` | `get_page_info()` | `ad_browser_page` + runtime page |
| `POST /auto-download/browser/page/activate` | `PageInfoResponse` | `browser_service.activate_page()` | `activate_page()` | Playwright `bring_to_front()`，页面状态同步 |
| `POST /auto-download/browser/page/close` | `ClosePageResponse` | `browser_service.close_page()` | `close_page()` | Playwright page close，页面失效 |
| `POST /auto-download/browser/bing-huya` | `BingHuyaRequest` / `PageInfoResponse` | `browser_service.bing_huya()` | `bing_huya()` | Bing 页面操作示例 |
| `GET /auto-download/browser/takeover/page-info` | `PageInfoResponse` | `browser_service.takeover_page_info()` | `takeover_latest_page_info()` | 接管未跟踪 runtime page |
| `POST /auto-download/browser/window/reopen` | `ReopenWindowResponse` | `browser_service.reopen_window()` | `reopen_window()` | 新窗口运行时 + 旧窗口失效 |
| `POST /auto-download/browser/window/invalidate` | `InvalidateWindowResponse` | `browser_service.invalidate_window()` | `invalidate_window()` | 窗口和页面状态失效 |
| `POST /auto-download/browser/close` | `InvalidateWindowResponse` | `browser_service.close_browser()` | `invalidate_window()` | 兼容关闭入口，当前语义为失效窗口 |

### 浏览器常见错误场景

| 场景 | 状态码 | 说明 |
| --- | --- | --- |
| `windowId` 为空 | 400 | 参数校验失败 |
| 窗口未初始化（未调 open） | 500 | `RuntimeError: browser not initialized` |
| browser 已被标记失效 | 500 | `RuntimeError: window is invalid` |
| page_id 不存在于 page_map | 500 | 页面已被关闭或窗口已失效 |
| 浏览器进程启动失败 | 500 | Chrome 路径错误 / CDP 挂接超时 |

---

## 桌面窗口 API

| 接口 | 请求/响应 schema | service | manager | 外部依赖 |
| --- | --- | --- | --- | --- |
| `GET /auto-download/desktop/windows` | `WindowQueryRequest` / `WindowListResponse` | `desktop_service.list_windows()` | `windows_manager.list_windows()` | `pywinauto.Desktop` |
| `POST /auto-download/desktop/window/activate` | `ActivateWindowRequest` / `ActivateWindowResponse` | `desktop_service.activate_window()` | `windows_manager.activate_window()` | `pywinauto` |
| `POST /auto-download/desktop/keyboard/type` | `TypeTextRequest` / `KeyboardActionResponse` | `desktop_service.type_text()` | service 内部执行 | `pyautogui.write()` |
| `POST /auto-download/desktop/keyboard/hotkey` | `HotkeyRequest` / `KeyboardActionResponse` | `desktop_service.hotkey()` | service 内部执行 | `pyautogui.hotkey()` |

### 桌面常见错误场景

| 场景 | 状态码 | 说明 |
| --- | --- | --- |
| 按标题激活但窗口未找到 | 400 | `ValueError: window not found` |
| `type_text` 目标未激活 | (无报错) | 文本会发送到当前前台窗口，而非目标窗口 |
| pywinauto 后端不可用 | 500 | 非 Windows 系统或 DPI 问题 |

---

## 图像/屏幕 API

| 接口 | 请求/响应 schema | service | manager | 外部依赖 |
| --- | --- | --- | --- | --- |
| `POST /auto-download/desktop/click/pos` | `ClickPositionRequest` / `ClickPositionResponse` | `visual_service.click_position()` | `screen_manager.click_position()` | `pyautogui.click()` |
| `POST /auto-download/desktop/click/image` | `ClickImageRequest` / `ClickImageResponse` | `visual_service.click_image()` | `screen_manager.click_image()` | `pyautogui.locateOnScreen()` |
| `POST /auto-download/desktop/click/ocr-text` | `OcrClickTextRequest` / `OcrClickTextResponse` | `visual_service.ocr_click_text_reserved()` | `screen_manager.ocr_click_text_reserved()` | 当前仅预留 |

### 图像/屏幕常见错误场景

| 场景 | 状态码 | 说明 |
| --- | --- | --- |
| 坐标点击 | (不报错) | 任何坐标都可通过，超出屏幕范围只是无实际效果 |
| 模板图未找到 | 200 但 data=false | 返回 `Result[bool]`，匹配失败时 `data=false` |
| OCR 接口调用 | 200 但 data=false | 当前始终返回 false（预留接口） |

---

## 本地 service 调用

本地 Python 代码直接调用 service，不经过 HTTP API 层：

```python
from app.services.browser_service import BrowserService
from app.services.desktop_service import DesktopService
from app.services.visual_service import VisualService

# 浏览器
browser = BrowserService()
result = browser.init_browser()
window_id = result.data

result = browser.open_url("https://example.com", new_page=True)
page_id = result.data.id

# 桌面
desktop = DesktopService()
windows = desktop.list_windows()
desktop.activate_window_by_title("计算器")
desktop.type_text("hello", interval=0.1)
desktop.hotkey(["ctrl", "c"])

# 图像
visual = VisualService()
visual.click(100, 200)
found = visual.template_click("C:/captcha.png")
```

### 本地调用的直接返回

本地调用直接获得 `Result[T]` 对象：

```python
result = browser.init_browser()
print(result.code)     # 200
print(result.message)  # "success"
print(result.data)     # window_id (str)
```

---

## Batch configured browser pages

| 接口 | 请求/响应 schema | service | manager | 外部依赖/数据库 |
| --- | --- | --- | --- | --- |
| `POST /auto-download/browser/page/batch-open-config` | `OpenConfiguredPagesRequest` / `BatchOpenPagesResponse` | `browser_service.open_config_pages()` | `open_config_pages()` | `ad_browser_page_config` + Playwright page + `ad_browser_page` |

请求中 `windowId` 或 `sessionId` 作为查询参数传递，`configCode` 和 `bringToFront` 在 JSON body 中传递。

**处理流程**:

1. 解析 windowId
2. 查询 ad_browser_page_config WHERE config_code = ? AND status = '1' ORDER BY sort_no, id
3. 遍历配置行，逐个 open_url()
4. 每个打开的页面写入 ad_browser_page 记录
5. 返回 total (配置行数) + openedPages (成功打开列表)

---

## 调用链总览

请求链路为 HTTP 客户端 → API 层 (async) → Service 层 (thread) → Manager 层 (核心逻辑)。Manager 层根据能力不同，调用 Playwright+CDP（浏览器）、pywinauto（桌面窗口）或 pyautogui+OpenCV（图像识别），浏览器操作还会经过 SQLAlchemy 写入 MySQL。

本地调用方直接接入 Service 层，不经过 HTTP 和 API 层。
