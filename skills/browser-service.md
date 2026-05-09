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
- `POST /browser/session/open-pure`
- `POST /browser/session/open-selenium`
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
- 当前默认按手动验证可用的快捷方式对齐：`BROWSER_EXECUTABLE_PATH=C:/software/chrome-win64/chrome.exe`、`PROFILE_DIR=C:/chrome_debug_profile`、`DEBUG_PORT=9222`。
- `OPEN_PAGE_MODE=native` 时，创建窗口和子页面优先走 Chrome 原生命令行，不优先走 `Target.createTarget` 或 `window.open`。
- `AUTO_CLICK_SECURITY_CHECK=false` 时，不自动点击 Cloudflare 等安全验证图片。
- 不要使用日常 Chrome 默认用户目录作为 `PROFILE_DIR`。
- `/browser/session/open-selenium` 使用 Selenium `debuggerAddress` 附加到 `127.0.0.1:DEBUG_PORT`，打开 URL 后立即 `driver.quit()` 断开，不保存全局 driver。
- `SELENIUM_CHROMEDRIVER_PATH` 为空时走 Selenium Manager 自动处理 chromedriver；离线或自动下载失败时再填本机 chromedriver 路径。

## 注意

FastAPI 路由层是 `async`，但浏览器 service 使用同步 Playwright 能力，所以 API 层必须使用 `run_in_threadpool()` 转调，避免在 asyncio loop 里直接执行 Playwright Sync API。

`BrowserService` 负责创建数据库会话并调用 manager，不要把 `SessionLocal()` 暴露给 API 层或本地业务代码。

## 当前推荐打开模式

当前推荐使用 `OPEN_PAGE_MODE=cdp_http`。该模式只使用 Chrome DevTools HTTP 请求打开页面，不再等待 Playwright Page 对象、`domcontentloaded`、标题或 iframe 加载完成，适合需要配合桌面图像识别的网页验证场景。

不要再优先使用 `OPEN_PAGE_MODE=native`，因为 native 模式会反复执行 `chrome.exe --new-window <url>`，在已有同 profile Chrome 实例时可能只是把请求转发给已有进程，导致页面肉眼已打开但 Playwright 无法在 `context.pages` 中识别新页面。

## Cloudflare 场景短接管约定

- `/biz/page-flow?configCode=...`：Playwright 短接管版。仅在打开配置页时临时连接 CDP，打开 URL 后立即断开，不长期保存 Playwright runtime。
- `/biz/page-flow-selenium?configCode=...`：Selenium 短接管复现版。通过 `debuggerAddress=127.0.0.1:9222` 附加到已有 Chrome，打开页面后立即 `driver.quit()`。
- 默认不读取页面标题、当前 URL，不等待 DOM、iframe 或 load。需要调试时再临时开启 `SELENIUM_READ_PAGE_INFO=true` 或 `PLAYWRIGHT_ONCE_READ_PAGE_INFO=true`。
- Cloudflare 验证阶段优先使用纯净打开或 Selenium 短接管，不建议使用长期 Playwright/CDP 接管。
