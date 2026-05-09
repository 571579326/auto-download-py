# 关键类与函数说明

## 1. 浏览器模块

### BrowserSessionManager (`app/browser/manager.py`)

浏览器会话管理核心类。一个实例管理一个浏览器窗口（一个 Chrome 进程），通过 Playwright Sync API + CDP 控制。

**类签名**:

```python
class BrowserSessionManager:
    def __init__(self, db_session: Session, logger: logging.Logger)
```

**属性**:

| 属性 | 类型 | 说明 |
| --- | --- | --- |
| `db` | Session | SQLAlchemy 数据库会话 |
| `logger` | Logger | 日志记录器 |
| `playwright` | Playwright \| None | Playwright 控制器实例 |
| `browser` | Browser \| None | Playwright Browser 实例 |
| `browser_context` | BrowserContext \| None | 浏览器上下文 |
| `default_page` | Page \| None | 默认页面（浏览器唯一 Page） |
| `window_orm` | AdBrowserWindow \| None | 数据库窗口 ORM 对象 |
| `window_id` | str \| None | 业务窗口 ID (UUID hex) |
| `page_map` | dict[int, _PageInfo] | 运行时页面映射表（orm-id → PageInfo） |

**PageInfo 结构**:

```python
@dataclass
class _PageInfo:
    orm_id: int              # ad_browser_page.id
    window_id: int           # ad_browser_window.id
    title: str               # 页面标题
    url: str                 # 页面 URL
    page: Page               # Playwright Page 对象
    status: str              # '1'=激活, '2'=失效
    page_index: int          # Playwright pages 列表中的索引
```

**核心方法**:

| 方法 | 说明 | 关键参数 | 返回值 |
| --- | --- | --- | --- |
| `open_window()` | 启动浏览器进程，创建窗口记录和根页面 | `page_config_json` (可选启动参数 JSON) | `str` (window_id) |
| `close_window()` | 关闭浏览器进程，窗口标记为失效 | 无 | `None` |
| `new_tab(url=None)` | 在当前浏览器打开新标签页 | `url` (导航目标 URL) | `AdBrowserPage` (ORM 对象) |
| `open_url(url, new_page=False)` | 在当前页面导航到 URL；`new_page=True` 时创建新标签页 | `url`, `new_page` | `AdBrowserPage` |
| `close_page(page_id)` | 关闭指定页面（按 orm_id） | `page_id` (int) | `None` |
| `reopen_window()` | 重新打开浏览器（旧窗口标记失效，所有页面恢复） | 无 | `str` (新 window_id) |
| `list_active_pages()` | 获取当前所有激活的页面列表 | 无 | `list[AdBrowserPage]` |
| `invalidate_window()` | 强制失效当前窗口（不关闭浏览器进程） | 无 | `None` |
| `invalidate_all_pages()` | 将当前窗口所有页面标记为失效 | 无 | `None` |
| `is_window_invalid()` | 检查窗口是否已被标记失效 | 无 | `bool` |
| `get_page_by_id(page_id)` | 按 orm_id 获取运行时页面 | `page_id` | `Page \| None` |

**私有辅助方法**:

| 方法 | 说明 |
| --- | --- |
| `_sync_open_page_record()` | 创建或更新 ad_browser_page 数据库记录 |
| `_sync_close_page_record()` | 将页面记录标记为失效 (status=2) |
| `_sync_close_window_record()` | 将窗口记录标记为失效 (status=0) |
| `_reset_page_map()` | 清空 page_map 字典 |
| `_launch_browser()` | 启动 Chrome 进程并挂接 CDP |
| `_new_context_page()` | 创建新的浏览器上下文页面 |

---

### BrowserService (`app/services/browser_service.py`)

浏览器业务服务层，隔离 API 层和 BrowserSessionManager。维护一个单线程池和当前会话引用。

**类签名**:

```python
class BrowserService:
    def __init__(self)
```

**属性**:

| 属性 | 类型 | 说明 |
| --- | --- | --- |
| `_executor` | ThreadPoolExecutor | `max_workers=1` 的单线程池 |
| `_loop` | AbstractEventLoop | 创建时的事件循环引用 |
| `_db_session` | Session \| None | 当前数据库会话 |

**核心方法**:

| 方法 | 说明 | 返回值 |
| --- | --- | --- |
| `init_browser(page_config_json=None)` | 初始化浏览器并打开窗口 | `Result[str]` (window_id) |
| `close_browser()` | 关闭浏览器 | `Result[None]` |
| `open_url(url, new_page=False)` | 打开 URL | `Result[AdBrowserPage]` |
| `new_tab(url=None)` | 新建标签页 | `Result[AdBrowserPage]` |
| `close_page(page_id)` | 关闭指定页面 | `Result[None]` |
| `reopen_browser()` | 重新打开浏览器 | `Result[str]` (新 window_id) |
| `list_active_pages()` | 列出活动页面 | `Result[list[AdBrowserPage]]` |
| `get_page_info(page_id)` | 获取指定页面的 URL 和标题 | `Result[dict]` |
| `list_all_pages()` | 从数据库查询窗口下的所有页面记录 | `Result[list[AdBrowserPage]]` |
| `batch_open_by_config(config_code)` | 根据配置编码批量打开页面组 | `Result[list[AdBrowserPage]]` |
| `list_browser_configs()` | 列出所有有效的页面配置组 | `Result[list[AdBrowserPageConfig]]` |
| `get_browser_window_id()` | 获取当前浏览器窗口 ID | `Result[str]` |
| `get_browser_status()` | 获取浏览器运行状态 | `Result[dict]` |

**浏览器状态返回值结构**:

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "is_running": true,
        "window_id": "abc123...",
        "window_invalid": false,
        "active_page_count": 3
    }
}
```

**关键设计**:

- `_executor` 是单线程 `ThreadPoolExecutor(max_workers=1)`，确保所有浏览器操作串行执行
- 所有公共方法用 `run_in_threadpool`（通过 `_run` 方法）包装，兼容异步 API 调用
- 每次操作创建新 `SessionLocal()`，完成后关闭
- 通过 `_ensure_manager()` 延迟初始化 `BrowserSessionManager`，确保先调 `init_browser()`

---

## 2. 桌面窗口模块

### WindowsManager (`app/desktop/windows_manager.py`)

基于 pywinauto 的桌面窗口管理模块。

**核心函数**:

| 函数 | 说明 | 参数 | 返回值 |
| --- | --- | --- | --- |
| `list_window_pids()` | 列举所有窗口标题、进程 PID 和类名 | 无 | `list[dict]` (每个 dict: `title`, `pid`, `class_name`) |
| `enum_window_titles_by_pid(pid)` | 按 PID 过滤窗口标题列表 | `pid: int` | `list[str]` |
| `activate_window_by_title(title)` | 按标题激活窗口（前置+聚焦） | `title: str` | `None` |
| `activate_top_window_by_pid(pid)` | 按 PID 激活最顶层窗口 | `pid: int` | `None` |
| `get_window_rect_by_title(title)` | 获取窗口位置和尺寸 | `title: str` | `dict` (x, y, width, height) |
| `get_all_window_info()` | 获取所有窗口完整信息（含 rect、可见性等） | 无 | `list[dict]` |

**filter helper**:

| 函数 | 说明 |
| --- | --- |
| `_filter_explorer_and_im()` | 过滤掉 explorer.exe、输入法等系统窗口 |
| `_get_real_pid()` | 获取 pywinauto Desktop 对象中的真实 PID |

---

### DesktopService (`app/services/desktop_service.py`)

桌面自动化业务服务层。

**类签名**:

```python
class DesktopService:
    def __init__(self)
```

**核心方法**:

| 方法 | 说明 | 关键参数 | 返回值 |
| --- | --- | --- | --- |
| `list_windows()` | 列出所有窗口 | 无 | `Result[list[dict]]` |
| `list_windows_by_pid(pid)` | 按 PID 列出窗口 | `pid: int` | `Result[list[str]]` |
| `activate_window_by_title(title)` | 激活窗口 | `title: str` | `Result[None]` |
| `activate_window_by_pid(pid)` | 按 PID 激活窗口 | `pid: int` | `Result[None]` |
| `type_text(text, interval=0.1)` | 在当前激活窗口输入文本（pyautogui） | `text: str, interval: float` | `Result[None]` |
| `hotkey(keys)` | 发送组合键（pyautogui） | `keys: list[str]` | `Result[None]` |

**注意**: `type_text` 和 `hotkey` 使用 `pyautogui` 发送全局事件，需要目标窗口已激活。

---

## 3. 图像/屏幕模块

### ScreenManager (`app/visual/screen_manager.py`)

屏幕截图、坐标点击、模板匹配点击的集中管理模块。

**核心函数**:

| 函数 | 说明 | 参数 | 返回值 |
| --- | --- | --- | --- |
| `screen_click(x, y, button='left')` | 在屏幕坐标 (x,y) 处点击 | `x: int, y: int, button: str` | `None` |
| `screen_double_click(x, y)` | 在屏幕坐标处双击 | `x: int, y: int` | `None` |
| `screen_move_to(x, y)` | 移动鼠标到屏幕坐标 | `x: int, y: int` | `None` |
| `screen_drag(start_x, start_y, end_x, end_y)` | 从起点拖拽到终点 | `start_x/y, end_x/y: int` | `None` |
| `screen_swipe(start_x, start_y, end_x, end_y)` | 从起点滑动到终点（不可见拖拽） | `start_x/y, end_x/y: int` | `None` |
| `template_click(template_path, button='left', timeout=3)` | 模板图匹配定位后点击 | `template_path: str` | `bool` (是否找到并点击成功) |
| `template_double_click(template_path, timeout=3)` | 模板图匹配后双击 | `template_path: str` | `bool` |
| `ocr_click(text)` | OCR 识别文字位置后点击（预留接口） | `text: str` | `False` (当前始终返回 False，未真正实现) |

**关键行为**:

- `template_click` 支持 `timeout` 参数（单位秒），在超时内循环匹配
- 所有 `template_*` 函数匹配成功后返回 `bool`，失败返回 `False`
- OCR 功能当前仅返回 `False`，需安装配置 `cnocr` 后方可使用

---

### VisualService (`app/services/visual_service.py`)

图像/屏幕服务层，透传调用 ScreenManager。

**核心方法**:

| 方法 | 说明 | 返回值 |
| --- | --- | --- |
| `click(x, y, button='left')` | 坐标点击 | `Result[None]` |
| `double_click(x, y)` | 坐标双击 | `Result[None]` |
| `move_to(x, y)` | 移动鼠标 | `Result[None]` |
| `drag(start_x, start_y, end_x, end_y)` | 拖拽 | `Result[None]` |
| `swipe(start_x, start_y, end_x, end_y)` | 滑动 | `Result[None]` |
| `template_click(template_path, button='left', timeout=3)` | 模板图点击 | `Result[bool]` |
| `template_double_click(template_path, timeout=3)` | 模板图双击 | `Result[bool]` |
| `ocr_click(text)` | OCR 点击（预留） | `Result[bool]` |

---

## 4. API 层

### 浏览器 API (`app/api/browser.py`)

FastAPI APIRouter，包含 15+ 个端点。

| HTTP 方法 | 路径 | 函数 | 说明 |
| --- | --- | --- | --- |
| `POST` | `/browser/init` | `init_browser` | 初始化浏览器 |
| `POST` | `/browser/close` | `close_browser` | 关闭浏览器 |
| `POST` | `/browser/open-url` | `open_url` | 打开 URL |
| `POST` | `/browser/new-tab` | `new_tab` | 新建标签页 |
| `POST` | `/browser/close-page` | `close_page` | 关闭标签页 |
| `POST` | `/browser/reopen` | `reopen_browser` | 重新打开浏览器 |
| `GET` | `/browser/pages` | `list_active_pages` | 列出活动页面 |
| `GET` | `/browser/pages/all` | `list_all_pages` | 列出所有页面记录 |
| `GET` | `/browser/page/{page_id}` | `get_page_info` | 获取页面详情 |
| `POST` | `/browser/batch-open` | `batch_open_by_config` | 批量打开配置页面 |
| `GET` | `/browser/configs` | `list_browser_configs` | 列出页面配置组 |
| `GET` | `/browser/window-id` | `get_browser_window_id` | 获取窗口 ID |
| `GET` | `/browser/status` | `get_browser_status` | 获取浏览器状态 |

### 桌面 API (`app/api/desktop.py`)

| HTTP 方法 | 路径 | 函数 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/desktop/window/list` | `list_windows` | 列出所有窗口 |
| `GET` | `/desktop/window/list-by-pid` | `list_windows_by_pid` | 按 PID 列出窗口 |
| `POST` | `/desktop/window/activate-title` | `activate_window_by_title` | 按标题激活窗口 |
| `POST` | `/desktop/window/activate-pid` | `activate_window_by_pid` | 按 PID 激活窗口 |
| `POST` | `/desktop/type-text` | `type_text` | 输入文本 |
| `POST` | `/desktop/hotkey` | `hotkey` | 发送组合键 |
| `POST` | `/desktop/screen/click` | `click` | 屏幕坐标点击 |
| `POST` | `/desktop/screen/template-click` | `template_click` | 模板图匹配点击 |

### 健康检查 API (`app/api/health.py`)

| HTTP 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 返回 `{"code": 200, "message": "ok", "data": {}}` |

---

## 5. 配置与工具类

### Settings (`app/core/config.py`)

基于 `pydantic-settings` 的配置模型。

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `app_context_path` | str | `/auto-download` | API 路由前缀 |
| `app_host` | str | `0.0.0.0` | 服务监听地址 |
| `app_port` | int | `8099` | 服务监听端口 |
| `app_reload` | bool | `True` | 开发时热重载 |
| `db_host` | str | `localhost` | 数据库地址 |
| `db_port` | int | `3306` | 数据库端口 |
| `db_user` | str | `root` | 数据库用户名 |
| `db_password` | str | `root` | 数据库密码 |
| `db_database` | str | `auto_download` | 数据库名称 |
| `log_dir` | str | `./logs` | 日志文件目录 |

**配置加载**:

- 所有字段支持 `.env` 文件覆盖
- `.env` 文件通过 `pyproject.toml` 中 `[tool.poe.env]` 加载
- 默认值适用于本地开发环境

### Result 通用响应模型 (`app/schemas/common.py`)

```python
class Result(BaseModel, Generic[T]):
    code: int = Field(default=200, ge=0)       # 状态码
    message: str = Field(default="success")     # 状态消息
    data: T | None = None                       # 响应数据
```

所有 API 接口统一返回此格式。

### 端口工具 (`app/utils/port_utils.py`)

| 函数 | 说明 |
| --- | --- |
| `is_port_available(port)` | 检查端口是否可用 |
| `find_available_port(start_port, end_port)` | 在范围内查找可用端口 |

### HTTP 工具 (`app/utils/http_utils.py`)

| 函数 | 说明 |
| --- | --- |
| `http_get_json(url)` | 发起 HTTP GET 请求，返回 JSON 数据（使用 requests 库） |

---

## 6. 数据库模型

### AdBrowserWindow (`app/models/browser_window.py`)

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | int | PK, autoincrement | 自增主键 |
| `window_id` | str | VARCHAR(64), UNIQUE, NOT NULL | 业务窗口 ID (UUID hex) |
| `status` | str | CHAR(1), default='1' | 1=有效, 0=失效 |
| `last_page_title` | str | VARCHAR(255), nullable | 最后激活页面标题 |
| `last_page_url` | str | VARCHAR(500), nullable | 最后激活页面 URL |

### AdBrowserPage (`app/models/browser_page.py`)

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | int | PK, autoincrement | 自增主键 |
| `window_id` | int | FK → ad_browser_window.id, NOT NULL | 所属窗口 |
| `title` | str | VARCHAR(255) | 页面标题 |
| `url` | str | VARCHAR(1000) | 页面 URL |
| `status` | str | CHAR(1) | 0=非激活, 1=激活, 2=失效 |
| `sort_no` | int | INT | 窗口内排序号 |

### AdBrowserPageConfig (`app/models/browser_page_config.py`)

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | int | PK, autoincrement | 自增主键 |
| `config_code` | str | VARCHAR(64) | 配置编码 |
| `config_name` | str | VARCHAR(255) | 配置名称 |
| `page_name` | str | VARCHAR(255) | 页面名称 |
| `url` | str | VARCHAR(1000) | 页面 URL |
| `status` | str | CHAR(1) | 1=有效, 0=失效 |
| `sort_no` | int | INT | 打开顺序 |

---

## 7. 关键枚举与常量

### 页面状态值

| 值 | 含义 | 使用场景 |
| --- | --- | --- |
| `'0'` | 非激活 | 页面存在但不在前台 |
| `'1'` | 激活 | 当前正显示的页面 |
| `'2'` | 失效 | 页面已被关闭 |

### 窗口状态值

| 值 | 含义 |
| --- | --- |
| `'0'` | 失效（浏览器已关闭） |
| `'1'` | 有效（浏览器正在运行） |

---

## 8. 启动函数

### `app/main.py` 关键函数

| 函数 | 说明 |
| --- | --- |
| `create_app()` | 创建 FastAPI 实例，注册异常处理器，挂载路由，设置生命周期事件 |
| `startup_event()` | 应用启动时执行：配置日志 (`setup_logging()`)，强制 Windows asyncio 策略 (`set_windows_event_loop_policy()`) |
| `shutdown_event()` | 应用关闭时执行：清理资源 |
| `value_error_handler()` | 捕获 `ValueError` 返回 400 响应 |
| `runtime_error_handler()` | 捕获 `RuntimeError` 返回 500 响应 |
| `general_exception_handler()` | 捕获未预期的 `Exception` 返回 500 响应 |
