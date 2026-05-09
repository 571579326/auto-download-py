# 架构说明

## 项目定位

`auto-download-py` 是一个 Python 3.11 / Windows 混合自动化服务。它同时支持两种入口：

- **本地 Python 代码**直接调用 `app/services/*.py`。
- **外部系统、未来前端或 Chrome 扩展**通过 FastAPI HTTP API 调用。

当前仓库没有 Vue 页面，也没有 Java controller/service/mapper/xml。`browser-extension/` 是未来 Chrome 扩展预留目录，不是当前前端实现。

## 整体架构分层

项目分为 4 层，从上到下依次是：

1. **API 层** (`app/api/*.py`) — FastAPI Router (async)，负责参数接收、schema 绑定、通过 `run_in_threadpool` 转调 Service、封装 `Result[T]` 响应
2. **Service 层** (`app/services/*.py`) — 业务服务层，也是本地调用入口；隔离 API 层与核心实现，管理线程池和数据库会话
3. **运行时层** — 包括浏览器管理器 (`app/browser/manager.py`, Playwright+CDP)、桌面窗口管理 (`app/desktop/windows_manager.py`, pywinauto)、图像/屏幕操作 (`app/visual/screen_manager.py`, pyautogui/OpenCV)
4. **外部基础设施** — Playwright / CDP / pywinauto / pyautogui / MySQL

本地 Python 调用方直接从 `app/services/*.py` 进入，不经过 HTTP API。

## 模块职责详表

| 层级 | 目录 | 核心文件 | 职责 |
| --- | --- | --- | --- |
| **启动入口** | `app/` | `main.py` | FastAPI 应用创建、路由挂载、异常处理器注册、生命周期管理 |
| **API 层** | `app/api` | `browser.py` | 浏览器 HTTP API 路由（15+ 接口） |
| | | `business.py` | 业务流程 HTTP API（page-flow 短接管版 + Selenium 复现版） |
| | | `desktop.py` | 桌面/屏幕 HTTP API 路由（11+ 接口，含 click-images/click-ocr-text/keyboard 等） |
| | | `health.py` | 健康检查接口 `GET /health` |
| **Service 层** | `app/services` | `browser_service.py` | 浏览器业务服务，管理单线程 ThreadPoolExecutor + DB Session |
| | | `business_service.py` | 业务流程服务（page-flow：打开配置页面 → 图像校验/点击） |
| | | `desktop_service.py` | 桌面窗口服务，封装 windows_manager + pyautogui 键盘操作 |
| | | `visual_service.py` | 图像/屏幕服务，透传调用 screen_manager |
| **浏览器运行时** | `app/browser` | `manager.py` | Playwright + CDP 浏览器进程管理、窗口/页面运行时与数据库同步 |
| **桌面窗口** | `app/desktop` | `windows_manager.py` | pywinauto 窗口枚举、过滤、激活 |
| **图像/屏幕** | `app/visual` | `screen_manager.py` | pyautogui 坐标点击、模板图匹配点击、OCR 点击预留 |
| **Schema** | `app/schemas` | `common.py` | 通用响应模型 `Result[T]` |
| | | `browser.py` | 浏览器请求/响应 Pydantic 模型（16 个） |
| | | `desktop.py` | 桌面/屏幕请求/响应 Pydantic 模型（16 个） |
| **数据模型** | `app/models` | `browser_window.py` | `AdBrowserWindow` ORM 模型 |
| | | `browser_page.py` | `AdBrowserPage` ORM 模型 |
| | | `browser_page_config.py` | `AdBrowserPageConfig` ORM 模型 |
| **数据库** | `app/db` | `session.py` | SQLAlchemy engine/SessionLocal 创建 |
| | | `base.py` | `DeclarativeBase` 基类 |
| **核心配置** | `app/core` | `config.py` | `Settings` 模型（pydantic-settings），读取 `.env` |
| | | `logging_config.py` | 日志配置（控制台 + RotatingFileHandler） |
| | | `asyncio_policy.py` | Windows 下强制 ProactorEventLoopPolicy |
| **工具** | `app/utils` | `port_utils.py` | 端口检测工具函数 |
| | | `http_utils.py` | HTTP GET/PUT JSON 工具函数 |
| | | `image_utils.py` | 图像点击工具函数（单图/多图/轮询/兼容旧版） |
| **数据库脚本** | `sql/` | `auto_download.sql` | MySQL 初始化 DDL（3 张表） |
| **示例脚本** | `scripts/` | `demo_browser.py` | 浏览器自动化本地调用示例 |
| | | `demo_desktop.py` | 桌面自动化本地调用示例 |
| | | `demo_hybrid.py` | 浏览器+桌面混合自动化示例 |
| | | `local_service_demo.py` | 本地 service 综合使用示例 |
| | | `smoke_test.py` | HTTP API 冒烟测试脚本 |

## 调用链路详解

### 浏览器链路

`app/api/browser.py` (async) → `run_in_threadpool()` → `app/services/browser_service.py` (单线程 ThreadPoolExecutor) → 创建 `SessionLocal()` → `app/browser/manager.py` (BrowserSessionManager) → Playwright Sync API + CDP + SQLAlchemy → 关闭 `SessionLocal()`

浏览器 API 层是 `async`，但 Playwright 使用同步 API。API 层必须使用 `run_in_threadpool()` 调 service，避免在 asyncio event loop 中直接执行同步 Playwright 操作。

`BrowserService` 内部用单线程 `ThreadPoolExecutor(max_workers=1)` 串行执行浏览器任务。每次调用都会创建 `SessionLocal()`，交给 `BrowserSessionManager` 执行业务和数据库同步，最后关闭数据库会话。

### 桌面窗口链路

`app/api/desktop.py` → `run_in_threadpool()` → `app/services/desktop_service.py` → 窗口列举/激活走 `app/desktop/windows_manager.py` (pywinauto)；文本输入/组合键在 service 内部直接使用 pyautogui

桌面能力按 Windows 设计。`type_text()` 和 `hotkey()` 使用 `pyautogui` 发送全局键盘事件，调用前应先确保目标窗口已激活。

### 图像/屏幕链路

`app/api/desktop.py` → `run_in_threadpool()` → `app/services/visual_service.py` → `app/visual/screen_manager.py` → pyautogui / OpenCV / Pillow

图像点击依赖屏幕截图与模板匹配，容易受 DPI 缩放、主题、分辨率和遮挡影响。OCR 点击当前只是预留接口，不默认安装或接入 `cnocr`。

### 本地 Python 直接调用链路

`本地业务脚本 / scripts/*.py` → `app/services/*_service.py` → `manager/runtime 层`

本地调用不经过 `app/api/*`。业务代码不要直接 import API 层，也不要直接管理 `SessionLocal()`。

## 路由前缀

FastAPI app 在 `app/main.py` 中挂载路由：

```python
app.include_router(health_router, prefix=settings.app_context_path)
app.include_router(browser_router, prefix=settings.app_context_path)
app.include_router(business_router, prefix=settings.app_context_path)
app.include_router(desktop_router, prefix=settings.app_context_path)
```

默认 `APP_CONTEXT_PATH=/auto-download`，因此接口完整路径是：

```text
/auto-download/health
/auto-download/browser/**
/auto-download/biz/**
/auto-download/desktop/**
```

如果 `.env` 中修改 `APP_CONTEXT_PATH`，文档中的 `/auto-download` 前缀需要对应替换。

## 异常处理

在 `app/main.py` 中统一注册了三个异常处理器：

| 异常类型 | HTTP 状态码 | 响应格式 | 说明 |
| --- | --- | --- | --- |
| `ValueError` | 400 | `{code: 400, message: "...", data: null}` | 参数校验/业务逻辑异常 |
| `RuntimeError` | 500 | `{code: 500, message: "...", data: null}` | 运行时错误，自动记录日志 |
| `Exception` | 500 | `{code: 500, message: "...", data: null}` | 未捕获异常，自动记录日志 |

## 数据库模型

### ad_browser_window
浏览器窗口记录，通过 `window_id` (UUID hex) 业务标识唯一。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT (PK) | 自增主键 |
| `window_id` | VARCHAR(64) UNIQUE | 业务窗口 ID (UUID hex) |
| `status` | CHAR(1) | 1=有效, 0=失效 |
| `last_page_title` | VARCHAR(255) | 最后激活页面标题 |
| `last_page_url` | VARCHAR(500) | 最后激活页面 URL |

### ad_browser_page
窗口内页面记录，通过 `window_id` 外键关联窗口。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT (PK) | 自增主键 |
| `window_id` | BIGINT (FK) | 关联 `ad_browser_window.id` |
| `title` | VARCHAR(255) | 页面标题 |
| `url` | VARCHAR(1000) | 页面 URL |
| `status` | CHAR(1) | 0=非激活, 1=激活, 2=失效 |
| `sort_no` | INT | 窗口内排序号 |

### ad_browser_page_config
可复用的浏览器页面配置组，用于批量打开接口。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT (PK) | 自增主键 |
| `config_code` | VARCHAR(64) | 配置编码（分组标识） |
| `config_name` | VARCHAR(255) | 配置名称 |
| `page_name` | VARCHAR(255) | 页面名称 |
| `url` | VARCHAR(1000) | 页面 URL |
| `status` | CHAR(1) | 1=有效, 0=失效 |
| `sort_no` | INT | 打开顺序 |

## 数据库边界

当前只有浏览器窗口和页面状态落库。桌面窗口、键盘输入、坐标点击、模板图点击当前不落库。后续如果要持久化这些能力，应先新增 model 和 SQL，再从对应 manager/service 明确写入边界。

## 浏览器窗口与页面生命周期

- `open_window()`: 创建窗口记录 (status=1) → 启动浏览器进程 → 挂接 CDP → 创建根页面 → 加入 page_map
- `new_tab()`: 创建子页面 → 加入 page_map
- `open_url()`: 导航或新建页面
- `close_page()`: 标记 status=2, 关闭 Playwright Page, 从 page_map 移除
- `reopen_window()`: 旧窗口失效, 创建新窗口, 恢复所有页面
- `invalidate_window()`: 窗口 status=0, 所有页面 status=2, 清除 page_map, 关闭浏览器

## Batch page config persistence

`ad_browser_page_config` stores reusable browser page URL groups. The batch-open API reads rows by `config_code`, filters `status='1'`, orders by `sort_no,id`, and writes opened runtime pages back to `ad_browser_page`.

## 业务公共方法层

当前业务层按“接口入口 -> 公共业务编排 -> 专项能力服务”的方式组织：

- `app/api/business.py`：只负责接收 `/biz/page-flow`、`/biz/page-flow-selenium` 参数，并调用 `BusinessService`。
- `app/services/business_service.py`：保留业务入口方法，不直接堆叠打开浏览器、等待页面、图像点击等细节。
- `app/services/business_common_service.py`：新增公共业务编排层，提供后续业务接口可复用的方法：
  - `build_page_flow_context`：统一生成业务上下文，并解析点击偏移参数；
  - `open_config_pages_by_mode`：按 `playwright_once` 或 `selenium_once` 打开配置页面；
  - `wait_page_stable`：页面打开后按配置等待稳定；
  - `find_and_click_images_for_flow`：统一调用图像点击公共服务并输出业务日志；
  - `build_page_flow_result`：统一组装 page-flow 返回体。
- `app/services/business_image_click_service.py`：专项公共能力，负责“循环查找图像 -> 命中后点击 -> 失败降级为返回结果”。

新增业务接口时，优先复用 `business_common_service`，不要在新 service 中复制 page-flow 的打开页面、sleep、识图点击、结果拼装逻辑。
