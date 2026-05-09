# rpa-common-methods skill

## 目标

提供按功能分类的通用自动化动作，让日常业务流程像影刀 RPA 一样组合公共动作，而非每个业务重复写 Playwright、PyAutoGUI、图像识别或重连逻辑。

所有 RPA 动作均支持 **HTTP 调用** 和 **本地 Python import** 两种使用方式。

## 分层架构

```text
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

## 页面定位参数

大部分网页 DOM 动作使用同一套页面定位参数：

```json
{
  "windowId": "浏览器窗口ID",
  "pageId": "可选，页面ID",
  "urlContains": "可选，URL关键字"
}
```

规则：
1. `windowId` 必传。
2. 传 `pageId` 时精确操作该页面。
3. 不传 `pageId` 但传 `urlContains` 时，优先找 URL 包含该关键字的页面。
4. 都不传时，优先使用当前活动页；活动页不可用时接管浏览器中的最新页面。

## 功能分类与接口

### 页面类（/rpa/page/**）

| 接口 | 公共方法 | 作用 |
|---|---|---|
| `POST /rpa/page/reconnect` | `rpa_page_service.reconnect` | 重连/接管已有页面 |
| `POST /rpa/page/info` | `rpa_page_service.info` | 获取页面标题、URL、pageId |
| `POST /rpa/page/list` | `rpa_page_service.list_pages` | 列出窗口下页面 |
| `POST /rpa/page/activate` | `rpa_page_service.activate` | 激活页面 |
| `POST /rpa/page/open-tab` | `rpa_page_service.open_tab` | 打开新标签页 |
| `POST /rpa/page/open-url` | `rpa_page_service.open_url` | 当前页或新标签打开 URL |
| `POST /rpa/page/reload` | `rpa_page_service.reload` | 刷新页面 |
| `POST /rpa/page/wait-load-state` | `rpa_page_service.wait_load_state` | 等待页面加载状态 |
| `POST /rpa/page/wait-url` | `rpa_page_service.wait_url_contains` | 等待 URL 包含关键字 |
| `POST /rpa/page/screenshot` | `rpa_page_service.screenshot` | 页面截图 |

### DOM 元素类（/rpa/element/**）

| 接口 | 公共方法 | 作用 |
|---|---|---|
| `POST /rpa/element/exists` | `rpa_element_service.exists` | 判断元素是否存在 |
| `POST /rpa/element/click` | `rpa_element_service.click` | 点击元素 |
| `POST /rpa/element/input` | `rpa_element_service.input` | 输入文本 |
| `POST /rpa/element/text` | `rpa_element_service.text` | 读取元素文本 |
| `POST /rpa/element/attribute` | `rpa_element_service.attribute` | 读取元素属性 |
| `POST /rpa/element/press` | `rpa_element_service.press` | 在元素上按键 |
| `POST /rpa/element/select` | `rpa_element_service.select` | select 下拉框选择 |

### 网页 UI 定位类（/rpa/locator/**）

用于替代影刀里的"捕获网页元素/查找网页元素"。只负责把页面上的候选元素找出来，返回推荐 selector、文本、属性、坐标等信息；真正点击/输入仍交给 `/rpa/element/**`。

| 接口 | 公共方法 | 作用 |
|---|---|---|
| `POST /rpa/locator/find` | `rpa_locator_service.find` | 按 selector、文本、标签、属性、role、placeholder 查找 |
| `POST /rpa/locator/describe` | `rpa_locator_service.describe` | 描述 selector 命中的第一个元素，返回 outerHTML 和推荐 selector |
| `POST /rpa/locator/count` | `rpa_locator_service.count` | 统计 selector 命中数量，可选只统计可见元素 |

### 图像类（/rpa/image/**）

| 接口 | 公共方法 | 作用 |
|---|---|---|
| `POST /rpa/image/locate` | `rpa_image_service.locate` | 查找图像但不点击 |
| `POST /rpa/image/wait` | `rpa_image_service.wait` | 等待图像出现，超时抛错 |
| `POST /rpa/image/click` | `rpa_image_service.click` | 查找并点击单张图像 |
| `POST /rpa/image/click-many` | `rpa_image_service.click_many` | 多图 OR/AND 点击 |

图像坐标基于屏幕左上角；`clickOffsetX/clickOffsetY` 基于匹配到的图片区域左上角。

### 鼠标、键盘、剪贴板

| 分类 | 接口 |
|---|---|
| 鼠标 | `/rpa/mouse/click`、`/rpa/mouse/move`、`/rpa/mouse/drag`、`/rpa/mouse/scroll` |
| 键盘 | `/rpa/keyboard/type`、`/rpa/keyboard/hotkey`、`/rpa/keyboard/press` |
| 剪贴板 | `/rpa/clipboard/set`、`/rpa/clipboard/get`、`/rpa/clipboard/paste` |

### 数据处理类（/rpa/data/**）

接口统一输入输出 `rows: list[dict]`，方便接在网页采集、接口返回、Excel/CSV 读写之后继续编排。

| 接口 | 公共方法 | 作用 |
|---|---|---|
| `POST /rpa/data/clean` | `rpa_data_service.clean_rows` | trim 字符串、去空行、字段改名、选择字段、填充空值 |
| `POST /rpa/data/filter` | `rpa_data_service.filter_rows` | 按 eq/contains/gt/regex/empty 等条件过滤 |
| `POST /rpa/data/sort` | `rpa_data_service.sort_rows` | 多字段排序 |
| `POST /rpa/data/unique` | `rpa_data_service.unique_rows` | 按字段或整行去重 |
| `POST /rpa/data/group-count` | `rpa_data_service.group_count` | 分组计数 |
| `POST /rpa/data/extract-regex` | `rpa_data_service.extract_regex` | 文本正则提取，支持命名分组 |
| `POST /rpa/data/read-file` | `rpa_data_service.read_file` | 读取 CSV/JSON/XLSX 为行数据 |
| `POST /rpa/data/write-file` | `rpa_data_service.write_file` | 写出 CSV/JSON/XLSX |

### 等待类（/rpa/wait/**）

| 接口 | 公共方法 | 作用 |
|---|---|---|
| `POST /rpa/wait/sleep` | `rpa_wait_service.sleep` | 固定时间等待 |
| `POST /rpa/wait/element` | `rpa_wait_service.element_exists` | 等待元素出现 |
| `POST /rpa/wait/image` | `rpa_wait_service.image_exists` | 等待图像出现 |
| `POST /rpa/wait/url` | `rpa_wait_service.url_contains` | 等待 URL 包含关键字 |

### 断言类（/rpa/assert/**）

| 接口 | 公共方法 | 作用 |
|---|---|---|
| `POST /rpa/assert/url-contains` | `rpa_assert_service.url_contains` | 断言 URL 包含指定文本 |
| `POST /rpa/assert/element-exists` | `rpa_assert_service.element_exists` | 断言元素存在 |
| `POST /rpa/assert/image-exists` | `rpa_assert_service.image_exists` | 断言图像存在 |
| `POST /rpa/assert/text-contains` | `rpa_assert_service.text_contains` | 断言元素文本包含指定内容 |

### 流程编排（/rpa/flow/run）

```text
POST /auto-download/rpa/flow/run
```

请求体中的每个 `step` 都是一个动作，`params` 就是该动作对应请求模型的字段。支持 `retryTimes` 失败重试和 `continueOnError` 失败后继续。

支持的 `action` 列表：

```text
page.reconnect / page.info / page.list / page.activate / page.open_tab / page.open_url / page.reload / page.wait_load_state / page.wait_url_contains / page.screenshot
element.exists / element.click / element.input / element.text / element.attribute / element.press / element.select
locator.find / locator.describe / locator.count
image.locate / image.wait / image.click / image.click_many
data.clean / data.filter / data.sort / data.unique / data.group_count / data.extract_regex / data.read_file / data.write_file
mouse.click / mouse.move / mouse.drag / mouse.scroll
keyboard.type / keyboard.hotkey / keyboard.press
clipboard.set / clipboard.get / clipboard.paste
wait.sleep / wait.element / wait.image / wait.url_contains
assert.element_exists / assert.image_exists / assert.url_contains / assert.text_contains
```

## 扩展顺序

新增 RPA 公共动作时：
1. `app/schemas/rpa.py` — 定义请求/响应模型
2. `app/services/rpa/rpa_xxx_service.py` — 实现公共方法
3. `app/api/rpa.py` — 注册 HTTP 路由
4. `app/services/rpa/rpa_flow_service.py` — 在 `_execute_step` 中注册 action
5. 同步文档：`docs/rpa-common-methods.md`、`skills/rpa-common-methods.md`

## 和业务层的关系

推荐分层：

```text
底层驱动：Playwright / PyAutoGUI / Windows API
        ↓
RPA公共方法层：app/services/rpa/**
        ↓
流程编排层：rpa_flow_service.py
        ↓
业务层：app/services/business_service.py
        ↓
接口层：app/api/**
```

后续新增具体业务，优先在 `/rpa/flow/run` 中组合公共动作；只有稳定复用的业务流程才再封装到 `/biz/**`。
