# auto-download-py 项目技能总纲

本文档按功能模块分层归纳项目能力，为后续维护者和自动化代理提供快速导航。

## 项目定位

`auto-download-py` 是一个面向 Windows 的 Python 混合自动化服务，核心能力包括浏览器自动化、桌面窗口自动化、屏幕/图像点击，以及供本地 Python 代码直接调用的 service 层。

项目同时满足两种调用方式：
1. **本地 Python 业务代码**直接 `import app.services.*` 调用。
2. **外部系统、前端或 Chrome 扩展**通过 FastAPI HTTP API 调用。

---

## 一、整体架构分层

```text
┌─────────────────────────────────────────────────────────────┐
│  API 层 (app/api/*.py)                                      │
│  FastAPI Router (async) — 参数接收、schema 绑定、线程池转调   │
├─────────────────────────────────────────────────────────────┤
│  Service 层 (app/services/*.py)                             │
│  业务服务层 — 本地调用入口，隔离 API 与核心实现               │
├─────────────────────────────────────────────────────────────┤
│  Manager/Runtime 层                                         │
│  ├─ app/browser/manager.py    (Playwright + CDP)           │
│  ├─ app/desktop/windows_manager.py  (pywinauto)            │
│  └─ app/visual/screen_manager.py    (pyautogui/OpenCV)     │
├─────────────────────────────────────────────────────────────┤
│  外部基础设施                                                │
│  Playwright / CDP / pywinauto / pyautogui / MySQL          │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、功能模块技能树

### 2.1 浏览器自动化 (Browser Automation)

**核心能力**：浏览器进程管理、窗口/标签页生命周期、页面导航、CDP 短接管、Selenium 短接管、数据库持久化。

**调用链**：
```text
HTTP API → BrowserService → BrowserSessionManager → Playwright/CDP + SQLAlchemy
```

**Skill 文档**：[skills/browser-service.md](skills/browser-service.md)

**关键文件**：
- `app/api/browser.py` — 浏览器 HTTP API 路由
- `app/services/browser_service.py` — 浏览器业务服务
- `app/browser/manager.py` — Playwright + CDP 浏览器运行时管理
- `app/models/browser_window.py` — 窗口 ORM
- `app/models/browser_page.py` — 页面 ORM
- `app/models/browser_page_config.py` — 页面配置 ORM

**主要接口**：
- `POST /browser/session/open` — 启动 Chrome 并建立 CDP 连接
- `POST /browser/session/open-pure` — 纯净模式启动（不挂接 Playwright）
- `POST /browser/session/open-selenium` — Selenium 短接管启动
- `POST /browser/window/open` / `reopen` / `invalidate` / `close`
- `POST /browser/tab/open` / `page/open-url` / `page/batch-open-config`
- `GET /browser/windows` / `pages` / `page-info`
- `POST /browser/page/activate` / `close`

---

### 2.2 页面操作与定位 (Page Operations)

**核心能力**：页面 ID 规则、页面定位优先级、激活页追踪、批量配置打开。

**Skill 文档**：[skills/page-operations.md](skills/page-operations.md)

**页面定位优先级**：
1. 传 `pageId` → 精确匹配
2. 传 `urlContains` → URL 模糊匹配
3. 都不传 → 取当前 active / 最近页面

**关键约定**：
- `pageId` 格式为 `page-{id}`（数据库主键派生）
- 以下操作会更新 active page：新建标签页、打开 URL（bringToFront=true）、接管页面、激活页面、关闭 active 页后同步

---

### 2.3 桌面窗口自动化 (Desktop Automation)

**核心能力**：窗口枚举、窗口激活、键盘输入、快捷键发送。

**调用链**：
```text
HTTP API → DesktopService → WindowsManager → pywinauto / pyautogui
```

**Skill 文档**：[skills/desktop-service.md](skills/desktop-service.md)

**关键文件**：
- `app/api/desktop.py` — 桌面/屏幕 HTTP API 路由
- `app/services/desktop_service.py` — 桌面业务服务
- `app/desktop/windows_manager.py` — pywinauto 窗口管理

**主要接口**：
- `GET /desktop/windows` — 枚举窗口
- `POST /desktop/window/activate` — 激活窗口（支持 handle/title/titleRegex/className）
- `POST /desktop/keyboard/type` — 文本输入
- `POST /desktop/keyboard/hotkey` — 组合键

---

### 2.4 图像/屏幕自动化 (Visual Automation)

**核心能力**：屏幕坐标点击、模板图像匹配点击、多图 OR/AND 点击、OCR 预留、DPI 感知。

**调用链**：
```text
HTTP API → VisualService → ScreenManager → pyautogui / OpenCV / Pillow
或：本地代码 → app/utils/image_utils.py → VisualService → ScreenManager
```

**Skill 文档**：[skills/visual-service.md](skills/visual-service.md) | [skills/business-image-click.md](skills/business-image-click.md)

**关键文件**：
- `app/visual/screen_manager.py` — 屏幕/图像核心逻辑
- `app/services/visual_service.py` — 图像业务服务
- `app/utils/image_utils.py` — 图像点击工具函数（本地直接 import）

**主要接口**：
- `POST /desktop/click/pos` — 坐标点击
- `POST /desktop/click/image` — 单图匹配点击
- `POST /desktop/click/images` — 多图 OR/AND 点击
- `POST /desktop/click/ocr-text` — OCR 点击（预留）

**工具函数**（`app/utils/image_utils.py`）：
- `click_image_until_found()` — 单图轮询点击
- `click_images_until_found()` — 多图轮询点击（支持 or/and）
- `click_image_if_exists()` — 兼容旧版的条件点击

---

### 2.5 业务流程编排 (Business Flow)

**核心能力**：配置页面批量打开、图像自动点击、业务公共编排、Cloudflare 安全验证绕过。

**调用链**：
```text
HTTP API → BusinessService → BusinessCommonService + BusinessImageClickService
         → BrowserService / VisualService / RPA Services
```

**Skill 文档**：[skills/business-image-click.md](skills/business-image-click.md)

**关键文件**：
- `app/api/business.py` — 业务流程 HTTP API
- `app/services/business_service.py` — 业务入口服务
- `app/services/business_common_service.py` — 业务公共编排层
- `app/services/business_image_click_service.py` — 业务图像点击服务

**主要接口**：
- `POST /biz/page-flow?configCode=...` — Playwright 短接管版业务流程
- `POST /biz/page-flow-selenium?configCode=...` — Selenium 短接管版业务流程

**业务编排方法**（`business_common_service.py`）：
- `build_page_flow_context()` — 统一生成业务上下文
- `open_config_pages_by_mode()` — 按模式打开配置页面
- `wait_page_stable()` — 等待页面稳定
- `find_and_click_images_for_flow()` — 统一识图点击
- `build_page_flow_result()` — 组装统一返回结构

---

### 2.6 RPA 公共方法层 (RPA Common Methods)

**核心能力**：按功能分类的通用自动化动作，支持 HTTP 调用和本地 Python import 两种方式。

**设计目标**：让日常业务流程像影刀 RPA 一样组合公共动作，而非每个业务重复写 Playwright/PyAutoGUI/图像识别逻辑。

**调用链**：
```text
HTTP API (/rpa/**) → RPA Service → BrowserManager / ScreenManager
或：本地代码 → import app.services.rpa.* → 直接调用
```

**关键文件**：`app/services/rpa/*.py`（共 11 个服务）

| 服务文件 | 功能分类 | 对应 HTTP 前缀 |
|---------|---------|--------------|
| `rpa_page_service.py` | 页面管理（重连、打开、刷新、截图） | `/rpa/page/**` |
| `rpa_element_service.py` | DOM 元素操作（点击、输入、读文本） | `/rpa/element/**` |
| `rpa_locator_service.py` | 网页 UI 定位（查找、描述、计数） | `/rpa/locator/**` |
| `rpa_image_service.py` | 图像查找/等待/点击 | `/rpa/image/**` |
| `rpa_mouse_service.py` | 鼠标动作（点击、移动、拖拽、滚轮） | `/rpa/mouse/**` |
| `rpa_keyboard_service.py` | 键盘输入（文本、快捷键、组合键） | `/rpa/keyboard/**` |
| `rpa_clipboard_service.py` | 剪贴板（设置、读取、粘贴） | `/rpa/clipboard/**` |
| `rpa_data_service.py` | 数据处理（清洗、过滤、排序、去重、文件读写） | `/rpa/data/**` |
| `rpa_wait_service.py` | 等待（sleep、等元素、等图像、等URL） | `/rpa/wait/**` |
| `rpa_assert_service.py` | 断言（URL、元素、文本、图像） | `/rpa/assert/**` |
| `rpa_flow_service.py` | JSON 流程编排（顺序执行、重试、失败策略） | `/rpa/flow/run` |

**详细说明**：[docs/rpa-common-methods.md](docs/rpa-common-methods.md)

---

### 2.7 基础设施与工具 (Infrastructure & Utils)

**核心能力**：配置管理、日志、数据库会话、HTTP 工具、端口工具、异常处理。

**关键文件**：
- `app/core/config.py` — pydantic-settings 配置模型（读取 `.env`）
- `app/core/logging_config.py` — 日志配置（控制台 + RotatingFileHandler）
- `app/core/asyncio_policy.py` — Windows ProactorEventLoopPolicy
- `app/db/session.py` — SQLAlchemy engine / SessionLocal
- `app/db/base.py` — DeclarativeBase 基类
- `app/schemas/common.py` — 通用响应模型 `Result[T]`
- `app/utils/http_utils.py` — HTTP GET/PUT JSON 工具
- `app/utils/port_utils.py` — 端口检测工具
- `app/utils/image_utils.py` — 图像点击工具函数

---

## 三、扩展顺序速查

### 新增浏览器能力
1. `app/schemas/browser.py`
2. `app/browser/manager.py`
3. `app/services/browser_service.py`
4. `app/api/browser.py`（仅在需要 HTTP 暴露时）
5. 同步文档：`README.md`、`docs/api-call-chain.md`、`skills/browser-service.md`

### 新增桌面窗口能力
1. `app/schemas/desktop.py`
2. `app/desktop/windows_manager.py`
3. `app/services/desktop_service.py`
4. `app/api/desktop.py`（仅在需要 HTTP 暴露时）
5. 同步文档：`README.md`、`docs/api-call-chain.md`、`skills/desktop-service.md`

### 新增图像/屏幕能力
1. `app/schemas/desktop.py`
2. `app/visual/screen_manager.py`
3. `app/services/visual_service.py`
4. `app/api/desktop.py`（仅在需要 HTTP 暴露时）
5. 同步文档：`README.md`、`docs/api-call-chain.md`、`skills/visual-service.md`

### 新增 RPA 公共动作
1. `app/schemas/rpa.py` — 定义请求/响应模型
2. `app/services/rpa/rpa_xxx_service.py` — 实现公共方法
3. `app/api/rpa.py` — 注册 HTTP 路由
4. `app/services/rpa/rpa_flow_service.py` — 在 `_execute_step` 中注册 action
5. 同步文档：`docs/rpa-common-methods.md`

---

## 四、文档索引

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目入口、快速启动、API 总览 |
| [AGENT.md](AGENT.md) | 给维护者或自动化代理使用的项目规则 |
| [SKILL.md](SKILL.md) | 本文档：按功能模块分层的技能总纲 |
| [docs/architecture.md](docs/architecture.md) | 项目分层、模块职责、调用链路、数据模型 |
| [docs/key-classes-functions.md](docs/key-classes-functions.md) | 核心类、函数、API 端点详细参考 |
| [docs/dependency-graph.md](docs/dependency-graph.md) | 外部/内部依赖、数据流、线程模型 |
| [docs/api-call-chain.md](docs/api-call-chain.md) | 接口到 schema、service、manager、数据库/外部依赖的映射 |
| [docs/development-guide.md](docs/development-guide.md) | 新增能力时的固定改动顺序和约束 |
| [docs/rpa-common-methods.md](docs/rpa-common-methods.md) | RPA 公共方法层详细说明 |
| [skills/browser-service.md](skills/browser-service.md) | 浏览器 service / API / manager 关系 |
| [skills/page-operations.md](skills/page-operations.md) | 标签页与页面定位规则 |
| [skills/desktop-service.md](skills/desktop-service.md) | 桌面窗口、键盘、窗口激活 |
| [skills/visual-service.md](skills/visual-service.md) | 坐标点击、模板图点击与 OCR 预留 |
| [skills/business-image-click.md](skills/business-image-click.md) | 业务公共图像点击服务 |
| [skills/commit-rules.md](skills/commit-rules.md) | PR 提交规范 |

---

## 五、核心约定

- **API 层只做参数接收、schema 绑定、线程池转调和统一响应封装**，不写核心逻辑。
- **业务代码优先调用 `app/services/*.py`**，不要直接调用 `app/api/*.py`。
- **不要把 `SessionLocal()` 暴露给上层业务代码**。
- **同步 Playwright API 不要直接在 FastAPI async 路由里执行**，必须使用 `run_in_threadpool()`。
- **当前没有 Vue 页面、Java controller/mapper/xml**，不要按 Vue+Java 结构假定目录存在。
- **浏览器操作使用单线程 ThreadPoolExecutor(max_workers=1)** 串行执行。
