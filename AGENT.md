# AGENT.md

## 项目定位

`auto-download-py` 是一个浏览器 + 桌面 + 图像的混合自动化项目，当前以后端服务和本地 Python service 为主。

项目需要同时满足两种调用方式：

1. 本地 Python 业务代码直接 import `app.services.*` 调用。
2. 外部系统、未来前端或 Chrome 扩展通过 FastAPI HTTP API 调用。

当前仓库没有 Vue 页面，也没有 Java controller/service/mapper/xml。不要按 Vue + Java 项目结构假定目录存在。

## 文档入口

- `README.md`：项目入口、快速启动、API 总览。
- `docs/architecture.md`：分层、模块职责、路由前缀、运行时和数据库边界。
- `docs/key-classes-functions.md`：核心类、函数、API 端点详细参考。
- `docs/dependency-graph.md`：外部/内部依赖关系、数据流、线程模型。
- `docs/api-call-chain.md`：接口到 schema、service、manager、外部依赖/数据库的映射。
- `docs/development-guide.md`：新增能力时的固定改动顺序和约束。
- `skills/*.md`：按能力拆分的维护说明。
  - `skills/business-image-click.md`：业务公共图像点击服务说明。

## 当前架构

- `app/api/*.py`
  - FastAPI router。
  - 只负责参数接收、schema 绑定、线程池转调和 `Result` 响应封装。
- `app/services/*.py`
  - 本地业务代码直接调用入口。
  - API 层和本地调用方都应复用这里。
  - `business_image_click_service.py`：业务公共图像点击服务，封装循环查找/按规则点击/结果返回的公共逻辑。
- `app/browser/manager.py`
  - 浏览器运行时与会话管理。
  - Playwright + CDP。
  - 窗口、页面列表、激活、关闭、接管、Bing 示例、重开窗口、失效窗口。
- `app/desktop/windows_manager.py`
  - Windows 窗口枚举与激活。
  - 基于 `pywinauto`。
- `app/visual/screen_manager.py`
  - 坐标点击、按图点击、OCR 预留。
  - 基于 `pyautogui`，模板图查找依赖 OpenCV/Pillow 能力。
- `app/models/*.py`
  - SQLAlchemy ORM。
  - 当前表为 `ad_browser_window`、`ad_browser_page`。
- `sql/auto_download.sql`
  - MySQL 初始化脚本。

## 调用链

浏览器 HTTP：

```text
调用方 -> app/api/browser.py -> app/services/browser_service.py -> app/browser/manager.py -> Playwright/CDP + SQLAlchemy
```

桌面窗口 HTTP：

```text
调用方 -> app/api/desktop.py -> app/services/desktop_service.py -> app/desktop/windows_manager.py -> pywinauto
```

图像/屏幕 HTTP：

```text
调用方 -> app/api/desktop.py -> app/services/visual_service.py -> app/visual/screen_manager.py -> pyautogui/OpenCV/Pillow
```

本地 Python：

```text
业务脚本 -> app/services/*_service.py -> manager/runtime 层
```

## 扩展规则

### 浏览器能力

新增浏览器能力时按顺序改：

1. `app/schemas/browser.py`
2. `app/browser/manager.py`
3. `app/services/browser_service.py`
4. `app/api/browser.py`，仅在需要 HTTP 暴露时
5. `README.md`、`docs/api-call-chain.md`、`skills/browser-service.md`

### 桌面窗口能力

新增窗口/桌面控件能力时按顺序改：

1. `app/schemas/desktop.py`
2. `app/desktop/windows_manager.py`
3. `app/services/desktop_service.py`
4. `app/api/desktop.py`，仅在需要 HTTP 暴露时
5. `README.md`、`docs/api-call-chain.md`、`skills/desktop-service.md`

### 图像/屏幕能力

新增坐标、模板图、OCR 能力时按顺序改：

1. `app/schemas/desktop.py`
2. `app/visual/screen_manager.py`
3. `app/services/visual_service.py`
4. `app/api/desktop.py`，仅在需要 HTTP 暴露时
5. `README.md`、`docs/api-call-chain.md`、`skills/visual-service.md`

## 不要做的事情

- 不要让业务代码直接 import `app.api.*`。
- 不要让 API 层直接写数据库。
- 不要在 API 层写浏览器/桌面/图像核心逻辑。
- 不要把桌面坐标点击和浏览器 DOM 操作混在一个 manager 里。
- 不要把 `SessionLocal()` 暴露给上层业务。
- 不要假定存在 Vue 页面、Java mapper 或 XML SQL 文件。

## 本版本边界

### 已完成

- 浏览器 service + API 双层结构。
- 桌面 service + API 双层结构。
- 图像/屏幕 service + API 双层结构。
- 业务公共图像点击服务（BusinessImageClickService）。
- 浏览器窗口和页面状态持久化。
- OCR 点击接口预留。
- uv 安装说明与脚本。

### 未默认完成

- Vue 前端。
- Chrome 扩展实际实现。
- cnOCR 真正接入。
- 桌面层持久化落库。
- 多会话多浏览器并发调度。
- 浏览器外部文件上传/另存为完整编排。

## 推荐测试顺序

1. `GET /auto-download/health`
2. `POST /auto-download/browser/session/open`
3. `GET /auto-download/browser/windows`
4. `GET /auto-download/browser/pages`
5. `POST /auto-download/browser/window/reopen`
6. `POST /auto-download/browser/window/invalidate`
7. `GET /auto-download/desktop/windows`
8. `POST /auto-download/desktop/window/activate`
9. `POST /auto-download/desktop/keyboard/type`
10. `POST /auto-download/desktop/click/pos`
11. `POST /auto-download/desktop/click/image`

## 日志排查建议

浏览器打开失败时，优先查看这些关键日志：

- `open_session开始`
- `浏览器进程已启动`
- `CDP已就绪`
- `数据库会话已写入`
- `sync_playwright启动成功`
- `connect_over_cdp成功`

如果失败，当前代码会尽量把 Chrome 提前退出、CDP 未就绪、Playwright 挂接失败的异常打印完整。
