# 依赖关系

## 1. 外部依赖（Python 包）

### 运行时核心依赖

| 包名 | 版本 | 用途 |
| --- | --- | --- |
| `fastapi` | >=0.111.0 | Web API 框架 |
| `uvicorn[standard]` | >=0.29.0 | ASGI 服务器 |
| `playwright` | >=1.44.0 | 浏览器自动化（CDP 协议 + 同步 API） |
| `pywinauto` | >=0.6.8 | Windows 桌面窗口枚举与激活 |
| `pyautogui` | >=0.9.54 | 屏幕坐标点击、模板图匹配、键盘事件 |
| `opencv-python` | >=4.9.0 | 模板图匹配（pyautogui 依赖） |
| `Pillow` | >=10.3.0 | 图像处理（pyautogui 依赖） |
| `pydantic-settings` | >=2.3.0 | 配置模型加载（读取 .env） |
| `SQLAlchemy` | >=2.0.31 | ORM 数据库框架 |
| `pymysql` | >=1.1.1 | MySQL 数据库驱动 |
| `requests` | >=2.32.0 | HTTP GET JSON 工具 |
| `pydantic` | >=2.7.0 | 请求/响应数据模型定义 |

### 开发/测试依赖

| 包名 | 版本 | 用途 |
| --- | --- | --- |
| `poethepoet` | >=0.27.0 | 任务运行器（运行 `poe` 命令） |
| `httpx` | >=0.27.0 | HTTP 客户端（smoke_test.py 中发送请求） |

### 可选/预留依赖

| 包名 | 说明 |
| --- | --- |
| `cnocr` | OCR 文字识别（`screen_manager.py` 中预留，当前未接入） |

> 所有依赖见 [pyproject.toml](file:///c:/code/py/auto-download-py/pyproject.toml) 中 `[project.dependencies]` 和 `[project.optional-dependencies]`。

---

## 2. 外部依赖关系

FastAPI/Uvicorn 是 HTTP 服务器入口，它依赖三方面能力：

- **pydantic** — 请求/响应 schema 校验与序列化
- **SQLAlchemy + pymysql** — 数据库 ORM 操作
- **run_in_threadpool** — asyncio 隔离，将同步调用分发到子线程

子线程中进一步调用底层的自动化库：**Playwright**（浏览器控制）、**pywinauto**（桌面窗口控制）、**pyautogui/OpenCV**（图像识别与屏幕操作）

---

## 3. 内部模块依赖

启动入口 `app/main.py` 挂载三个路由模块：

- `app/api/browser.py` → 依赖 `schemas/common.py`, `schemas/browser.py`, `services/browser_service.py` → 进一步依赖 `browser/manager.py` → 依赖 `models/*`, `db/session.py`, `db/base.py`
- `app/api/desktop.py` → 依赖 `schemas/common.py`, `schemas/desktop.py`, `services/desktop_service.py` 和 `services/visual_service.py` → `desktop_service` 依赖 `desktop/windows_manager.py` 和 pyautogui；`visual_service` 依赖 `visual/screen_manager.py`
- `app/api/health.py` → 无内部依赖

共享依赖：`app/core/config.py` 被所有模块引用；`app/core/logging_config.py` 和 `app/core/asyncio_policy.py` 被 `app/main.py` 在 startup 时调用；`app/utils/port_utils.py` 和 `app/utils/http_utils.py` 被 `browser/manager.py` 调用。

### 依赖方向规则

1. **单向依赖**: API → Service → Manager/Domain → Database
2. **禁止反向依赖**: Manager/Domain 不能依赖 Service 或 API
3. **禁止跨层跳过**: API 不能直接调用 Manager（必须经过 Service）
4. **Schema 共享**: API 层和 Service 层共同使用 `app/schemas/` 中的模型
5. **配置全局共享**: `settings` 对象可在任何层级导入

### 常见的错误依赖（禁止）

- `app/api/browser.py` 直接 import `app/browser/manager.py` — 必须经过 `app/services/browser_service.py`
- `app/browser/manager.py` 直接 import `app/services/browser_service.py` — Manager 层不能反向依赖 Service 层
- `scripts/*.py` 直接管理 `SessionLocal()` — 应该通过 `app/services/*.py` 调用

---

## 4. 模块间数据流

### 浏览器模块数据流

API 层 (`app/api/browser.py`) 接收 HTTP Request (Pydantic schema)，发送到 Service 层 (`app/services/browser_service.py`)。Service 创建 `SessionLocal()`，初始化 `BrowserSessionManager(db, logger)` 执行浏览器操作（Playwright → Chrome / CDP → DevTools Protocol），同时通过 SQLAlchemy 写入 MySQL。操作完成后关闭 `SessionLocal()`，返回 `Result[T]` 给 API 层。

### 桌面模块数据流

API 层 (`app/api/desktop.py`) 接收 HTTP Request，发送到 Service 层 (`app/services/desktop_service.py`)。窗口列举/激活操作调用 `windows_manager.py`（pywinauto），文本输入/组合键直接使用 pyautogui。返回 `Result[None / list[dict]]`。

### 图像模块数据流

API 层 (`app/api/desktop.py`) 接收 HTTP Request，发送到 Service 层 (`app/services/visual_service.py`)，透传调用 `screen_manager.py`：坐标点击/双击使用 pyautogui，模板图匹配使用 OpenCV match，OCR 为预留接口。返回 `Result[None / bool]`。

---

## 5. 线程模型

### 关键线程约束

主线程 (asyncio event loop) 运行 FastAPI async handlers。通过 `run_in_threadpool()` 将同步操作分发到子线程：

- `DesktopService` 和 `VisualService` 使用默认 ThreadPoolExecutor，无额外线程池约束
- `BrowserService._executor` 使用专用的 `ThreadPoolExecutor(max_workers=1)`，保证所有浏览器操作**串行**执行

**重要规则**:

- `BrowserService` 使用 `max_workers=1` 的专用线程池，保证所有浏览器操作**串行**执行
- `DesktopService` 和 `VisualService` 没有线程池限制，每次 API 调用在独立线程中执行
- API 层是 async，但 Playwright 和 pywinauto/pyautogui 都是同步调用，必须用 `run_in_threadpool` 隔离

---

## 6. 启动流程依赖

1. 读取 .env 配置 — `app/core/config.py` (pydantic-settings)，生成全局 settings 对象
2. 创建 FastAPI 应用 — `app/main.py: create_app()`，注册异常处理器 (ValueError→400, RuntimeError→500, Exception→500)，挂载路由 (health / browser / desktop)
3. 启动事件 (startup) — 配置日志 (`app/core/logging_config.py`，控制台 + RotatingFileHandler)，设置 Windows asyncio 策略 (`app/core/asyncio_policy.py`，ProactorEventLoopPolicy)
4. uvicorn 启动 — 监听 host={app_host} port={app_port}

---

## 7. 项目文件依赖矩阵

| 文件 | 依赖的内部模块 |
| --- | --- |
| `app/main.py` | api/*, core/config, core/logging_config, core/asyncio_policy |
| `app/api/browser.py` | schemas/common, schemas/browser, services/browser_service |
| `app/api/desktop.py` | schemas/common, schemas/desktop, services/desktop_service, services/visual_service |
| `app/api/health.py` | schemas/common |
| `app/services/browser_service.py` | core/config, db/session, browser/manager, schemas/common |
| `app/services/desktop_service.py` | desktop/windows_manager, schemas/common, pyautogui |
| `app/services/visual_service.py` | visual/screen_manager, schemas/common |
| `app/browser/manager.py` | models/*, db/session, db/base, core/config, utils/*, playwright |
| `app/desktop/windows_manager.py` | pywinauto |
| `app/visual/screen_manager.py` | pyautogui, opencv-python, Pillow |
| `app/schemas/browser.py` | pydantic |
| `app/schemas/desktop.py` | pydantic |
| `app/schemas/common.py` | pydantic (Generic[T]) |
| `app/db/session.py` | core/config, SQLAlchemy |
| `app/db/base.py` | SQLAlchemy DeclarativeBase |
| `app/core/config.py` | pydantic-settings |
| `app/core/logging_config.py` | logging (stdlib), core/config |
| `app/core/asyncio_policy.py` | asyncio (stdlib) |
| `app/models/*.py` | db/base, SQLAlchemy |
| `app/utils/port_utils.py` | socket (stdlib) |
| `app/utils/http_utils.py` | requests |
