# API 调用链

默认接口前缀为 `/auto-download`，由 `.env` 中的 `APP_CONTEXT_PATH` 控制。

## 健康检查

| 接口 | API 函数 | service / manager | 说明 |
| --- | --- | --- | --- |
| `GET /auto-download/health` | `app/api/health.py::health` | 无 | 返回服务健康状态 |

## 浏览器 API

| 接口 | 请求/响应 schema | service | manager | 外部依赖/数据库 |
| --- | --- | --- | --- | --- |
| `POST /auto-download/browser/session/open` | `OpenWindowResponse` | `browser_service.open_browser()` | `open_window()` | Playwright/CDP，`ad_browser_window` |
| `POST /auto-download/browser/window/open` | `OpenWindowResponse` | `browser_service.open_browser()` | `open_window()` | 同上，兼容窗口命名 |
| `GET /auto-download/browser/windows` | `WindowListResponse` | `browser_service.list_windows()` | `list_windows()` | `ad_browser_window` |
| `POST /auto-download/browser/tab/open` | `NewTabRequest` / `PageInfoResponse` | `browser_service.new_tab()` | `new_tab()` | Playwright page，`ad_browser_page` |
| `POST /auto-download/browser/page/open-url` | `OpenUrlRequest` / `PageInfoResponse` | `browser_service.open_url()` | `open_url()` | Playwright page，`ad_browser_page` |
| `GET /auto-download/browser/pages` | `PageListResponse` | `browser_service.list_pages()` | `list_pages()` | `ad_browser_page` + runtime page |
| `GET /auto-download/browser/page-info` | `PageInfoResponse` | `browser_service.get_page_info()` | `get_page_info()` | `ad_browser_page` + runtime page |
| `POST /auto-download/browser/page/activate` | `PageInfoResponse` | `browser_service.activate_page()` | `activate_page()` | Playwright `bring_to_front()`，页面状态同步 |
| `POST /auto-download/browser/page/close` | `ClosePageResponse` | `browser_service.close_page()` | `close_page()` | Playwright page close，页面失效 |
| `POST /auto-download/browser/bing-huya` | `BingHuyaRequest` / `PageInfoResponse` | `browser_service.bing_huya()` | `bing_huya()` | Bing 页面操作示例 |
| `GET /auto-download/browser/takeover/page-info` | `PageInfoResponse` | `browser_service.takeover_page_info()` | `takeover_latest_page_info()` | 接管未跟踪 runtime page |
| `POST /auto-download/browser/window/reopen` | `ReopenWindowResponse` | `browser_service.reopen_window()` | `reopen_window()` | 新窗口运行时 + 旧窗口失效 |
| `POST /auto-download/browser/window/invalidate` | `InvalidateWindowResponse` | `browser_service.invalidate_window()` | `invalidate_window()` | 窗口和页面状态失效 |
| `POST /auto-download/browser/close` | `InvalidateWindowResponse` | `browser_service.close_browser()` | `invalidate_window()` | 兼容关闭入口，当前语义为失效窗口 |

浏览器接口需要 `windowId` 或兼容参数 `sessionId`。API 层通过 `_resolve_window_id()` 解析，解析失败返回 `ValueError('windowId不能为空')`。

## 桌面窗口 API

| 接口 | 请求/响应 schema | service | manager | 外部依赖 |
| --- | --- | --- | --- | --- |
| `GET /auto-download/desktop/windows` | `WindowQueryRequest` / `WindowListResponse` | `desktop_service.list_windows()` | `windows_manager.list_windows()` | `pywinauto.Desktop` |
| `POST /auto-download/desktop/window/activate` | `ActivateWindowRequest` / `ActivateWindowResponse` | `desktop_service.activate_window()` | `windows_manager.activate_window()` | `pywinauto` |
| `POST /auto-download/desktop/keyboard/type` | `TypeTextRequest` / `KeyboardActionResponse` | `desktop_service.type_text()` | service 内部执行 | `pyautogui.write()` |
| `POST /auto-download/desktop/keyboard/hotkey` | `HotkeyRequest` / `KeyboardActionResponse` | `desktop_service.hotkey()` | service 内部执行 | `pyautogui.hotkey()` |

## 图像/屏幕 API

| 接口 | 请求/响应 schema | service | manager | 外部依赖 |
| --- | --- | --- | --- | --- |
| `POST /auto-download/desktop/click/pos` | `ClickPositionRequest` / `ClickPositionResponse` | `visual_service.click_position()` | `screen_manager.click_position()` | `pyautogui.click()` |
| `POST /auto-download/desktop/click/image` | `ClickImageRequest` / `ClickImageResponse` | `visual_service.click_image()` | `screen_manager.click_image()` | `pyautogui.locateOnScreen()` |
| `POST /auto-download/desktop/click/ocr-text` | `OcrClickTextRequest` / `OcrClickTextResponse` | `visual_service.ocr_click_text_reserved()` | `screen_manager.ocr_click_text_reserved()` | 当前仅预留 |

## 本地 service 调用

本地 Python 代码直接调用 service：

```python
from app.services.browser_service import browser_service
from app.services.desktop_service import desktop_service
from app.services.visual_service import visual_service
```

## Batch configured browser pages

| API | Request / response schema | service | manager | External dependency / database |
| --- | --- | --- | --- | --- |
| `POST /auto-download/browser/page/batch-open-config` | `OpenConfiguredPagesRequest` / `BatchOpenPagesResponse` | `browser_service.open_config_pages()` | `open_config_pages()` | `ad_browser_page_config` + Playwright page + `ad_browser_page` |

The request keeps the existing browser API shape: `windowId` or `sessionId` is passed as a query parameter, while `configCode` and `bringToFront` are passed in the JSON body.

本地调用不要 import `app.api.*`。API 层只是 HTTP 封装，不是业务复用入口。
