# browser-service skill

## 目标

让本地 Python 业务代码像调用 service 一样调用浏览器能力，同时保留 HTTP API 暴露能力。

详细调用链见 `../docs/api-call-chain.md`。

## 关键文件

- `app/schemas/browser.py`
- `app/browser/manager.py`
- `app/services/browser_service.py`
- `app/api/browser.py`
- `app/models/browser_window.py`
- `app/models/browser_page.py`
- `app/models/browser_page_config.py`
- `sql/auto_download.sql`

## 当前方法

- `open_browser()`
- `list_windows()`
- `new_tab()`
- `open_url()`
- `open_config_pages()`
- `list_pages()`
- `get_page_info()`
- `takeover_page_info()`
- `activate_page()`
- `close_page()`
- `bing_huya()`
- `reopen_window()`
- `invalidate_window()`
- `close_browser()`

## HTTP 入口

默认带 `/auto-download` 前缀：

- `POST /browser/session/open`
- `POST /browser/window/open`
- `GET /browser/windows`
- `POST /browser/tab/open`
- `POST /browser/page/open-url`
- `POST /browser/page/batch-open-config`
- `GET /browser/pages`
- `GET /browser/page-info`
- `POST /browser/page/activate`
- `POST /browser/page/close`
- `POST /browser/bing-huya`
- `GET /browser/takeover/page-info`
- `POST /browser/window/reopen`
- `POST /browser/window/invalidate`
- `POST /browser/close`

## 扩展顺序

1. `app/schemas/browser.py`
2. `app/browser/manager.py`
3. `app/services/browser_service.py`
4. `app/api/browser.py`，仅在需要 HTTP 暴露时
5. 文档同步

## Chrome 扩展工具栏

- `/browser/session/open` 通过 `chrome.exe --new-window` 创建原生 Chrome 窗口，再通过 CDP 接管页面。
- `BROWSER_EXECUTABLE_PATH` 推荐指向正常安装版 Chrome；Chrome for Testing 的扩展工具栏行为需要手动验收。
- `PROFILE_DIR` 必须是已经安装目标扩展的 profile，启动服务前不要让其他 Chrome 进程占用同一个 profile。

## 注意

FastAPI 路由层是 `async`，但浏览器 service 使用同步 Playwright 能力，所以 API 层必须使用 `run_in_threadpool()` 转调，避免在 asyncio loop 里直接执行 Playwright Sync API。

`BrowserService` 负责创建数据库会话并调用 manager，不要把 `SessionLocal()` 暴露给 API 层或本地业务代码。
