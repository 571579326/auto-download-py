# RPA 公共方法层说明

本项目新增 `app/services/rpa/`，按功能分类封装常用自动化动作。设计目标是让日常业务流程像影刀 RPA 一样组合公共动作，而不是每个业务都重复写 Playwright、PyAutoGUI、图像识别或重连逻辑。

## 目录结构

```text
app/services/rpa/
├─ rpa_page_service.py        # 页面：重连、页面信息、打开URL、刷新、截图、等待URL/加载状态
├─ rpa_element_service.py     # DOM元素：存在判断、点击、输入、读文本、读属性、按键、select选择
├─ rpa_locator_service.py     # 网页UI定位：查找元素、描述元素、统计元素、推荐selector
├─ rpa_image_service.py       # 图像：查找、等待、单图点击、多图点击
├─ rpa_mouse_service.py       # 鼠标：坐标点击、移动、拖拽、滚轮
├─ rpa_keyboard_service.py    # 键盘：文本输入、快捷键、单键/组合键
├─ rpa_clipboard_service.py   # 剪贴板：设置文本、读取文本、粘贴
├─ rpa_data_service.py        # 数据处理：清洗、过滤、排序、去重、分组、正则、读写文件
├─ rpa_wait_service.py        # 等待：sleep、等页面、等URL、等元素、等图像
├─ rpa_assert_service.py      # 断言：URL、元素、文本、图像
└─ rpa_flow_service.py        # JSON流程编排：顺序执行、失败重试、失败是否继续
```

接口统一挂在：

```text
/auto-download/rpa/**
```

如果你的 `.env` 中 `APP_CONTEXT_PATH` 不是 `/auto-download`，以实际配置为准。

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

## 页面类方法

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

示例：

```json
POST /auto-download/rpa/page/reconnect
{
  "windowId": "xxx",
  "urlContains": "example.com"
}
```

## DOM 元素类方法

| 接口 | 公共方法 | 作用 |
|---|---|---|
| `POST /rpa/element/exists` | `rpa_element_service.exists` | 判断元素是否存在 |
| `POST /rpa/element/click` | `rpa_element_service.click` | 点击元素 |
| `POST /rpa/element/input` | `rpa_element_service.input` | 输入文本 |
| `POST /rpa/element/text` | `rpa_element_service.text` | 读取元素文本 |
| `POST /rpa/element/attribute` | `rpa_element_service.attribute` | 读取元素属性 |
| `POST /rpa/element/press` | `rpa_element_service.press` | 在元素上按键 |
| `POST /rpa/element/select` | `rpa_element_service.select` | select 下拉框选择 |

示例：

```json
POST /auto-download/rpa/element/input
{
  "windowId": "xxx",
  "selector": "input[name='q']",
  "text": "测试内容",
  "clearFirst": true,
  "pressEnter": true,
  "timeoutMs": 5000
}
```


## 网页 UI 定位类方法

这一层用于替代影刀里的“捕获网页元素/查找网页元素”。它只负责把页面上的候选元素找出来，并返回推荐 selector、文本、属性、坐标等信息；真正点击/输入仍交给 `/rpa/element/**`。

| 接口 | 公共方法 | 作用 |
|---|---|---|
| `POST /rpa/locator/find` | `rpa_locator_service.find` | 按 selector、文本、标签、属性、role、placeholder 查找网页元素 |
| `POST /rpa/locator/describe` | `rpa_locator_service.describe` | 描述 selector 命中的第一个元素，返回 outerHTML 和推荐 selector |
| `POST /rpa/locator/count` | `rpa_locator_service.count` | 统计 selector 命中数量，可选只统计可见元素 |

示例：按文本查找按钮。

```json
POST /auto-download/rpa/locator/find
{
  "windowId": "xxx",
  "textContains": "登录",
  "tagNames": ["button", "a"],
  "visibleOnly": true,
  "maxResults": 10
}
```

示例：描述一个输入框 selector。

```json
POST /auto-download/rpa/locator/describe
{
  "windowId": "xxx",
  "selector": "input[name='q']",
  "includeHtml": true
}
```

返回里的 `suggestedSelectors` 可以直接复制到 `/rpa/element/click`、`/rpa/element/input`、`/rpa/element/text` 使用。

## 图像类方法

| 接口 | 公共方法 | 作用 |
|---|---|---|
| `POST /rpa/image/locate` | `rpa_image_service.locate` | 查找图像但不点击 |
| `POST /rpa/image/wait` | `rpa_image_service.wait` | 等待图像出现，超时抛错 |
| `POST /rpa/image/click` | `rpa_image_service.click` | 查找并点击单张图像 |
| `POST /rpa/image/click-many` | `rpa_image_service.click_many` | 多图 OR/AND 点击 |

图像坐标基于屏幕左上角；`clickOffsetX/clickOffsetY` 基于匹配到的图片区域左上角。

示例：

```json
POST /auto-download/rpa/image/click
{
  "imagePath": "C:/code/py/auto-download-py/app/visual/templates/search.png",
  "confidence": 0.8,
  "timeoutMs": 10000,
  "retryIntervalMs": 400,
  "clickOffsetX": 10,
  "clickOffsetY": 5
}
```

## 鼠标、键盘、剪贴板

| 分类 | 接口 |
|---|---|
| 鼠标 | `/rpa/mouse/click`、`/rpa/mouse/move`、`/rpa/mouse/drag`、`/rpa/mouse/scroll` |
| 键盘 | `/rpa/keyboard/type`、`/rpa/keyboard/hotkey`、`/rpa/keyboard/press` |
| 剪贴板 | `/rpa/clipboard/set`、`/rpa/clipboard/get`、`/rpa/clipboard/paste` |

示例：

```json
POST /auto-download/rpa/keyboard/hotkey
{
  "keys": ["ctrl", "s"]
}
```

```json
POST /auto-download/rpa/clipboard/set
{
  "text": "需要粘贴的大段文本"
}
```


## 数据处理类方法

这一层对应影刀中常用的数据表格、文本处理、列表处理能力。接口统一输入输出 `rows: list[dict]`，方便接在网页采集、接口返回、Excel/CSV 读写之后继续编排。CSV 使用标准库；Excel 优先走 `pandas + openpyxl`。

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

示例：过滤并去重。

```json
POST /auto-download/rpa/data/filter
{
  "rows": [
    {"name": "A", "status": "成功", "amount": "10"},
    {"name": "B", "status": "失败", "amount": "3"}
  ],
  "logic": "and",
  "conditions": [
    {"field": "status", "op": "eq", "value": "成功"},
    {"field": "amount", "op": "gt", "value": 5}
  ]
}
```

示例：从文本中提取订单号。

```json
POST /auto-download/rpa/data/extract-regex
{
  "text": "订单号：SO20260509001，金额：123.45",
  "pattern": "订单号：(?P<orderNo>\\w+)，金额：(?P<amount>[\\d.]+)"
}
```

## Flow 编排

接口：

```text
POST /auto-download/rpa/flow/run
```

示例：

```json
{
  "windowId": "xxx",
  "steps": [
    {
      "name": "接管页面",
      "action": "page.reconnect",
      "params": {"urlContains": "bing.com"}
    },
    {
      "name": "输入搜索词",
      "action": "element.input",
      "params": {
        "selector": "textarea[name='q'], input[name='q']",
        "text": "测试内容",
        "clearFirst": true,
        "pressEnter": true
      },
      "retryTimes": 1
    },
    {
      "name": "等待结果页",
      "action": "wait.url_contains",
      "params": {
        "urlContainsTarget": "search",
        "timeoutMs": 10000
      }
    },
    {
      "name": "截图留痕",
      "action": "page.screenshot",
      "params": {"fullPage": true}
    }
  ]
}
```

支持的 `action`：

```text
page.reconnect
page.info
page.list
page.activate
page.open_tab
page.open_url
page.reload
page.wait_load_state
page.wait_url_contains
page.screenshot

element.exists
element.click
element.input
element.text
element.attribute
element.press
element.select

locator.find
locator.describe
locator.count

image.locate
image.wait
image.click
image.click_many

data.clean
data.filter
data.sort
data.unique
data.group_count
data.extract_regex
data.read_file
data.write_file

mouse.click
mouse.move
mouse.drag
mouse.scroll

keyboard.type
keyboard.hotkey
keyboard.press

clipboard.set
clipboard.get
clipboard.paste

wait.sleep
wait.element
wait.image
wait.url_contains

assert.element_exists
assert.image_exists
assert.url_contains
assert.text_contains
```

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

后续新增具体业务，例如“打开页面、搜索、导出、等待下载”，优先在 `/rpa/flow/run` 中组合公共动作；只有稳定复用的业务流程才再封装到 `/biz/**`。


## 仍未实现、后续可继续补齐的影刀类基础能力

下面这些能力还没有在当前项目里完整实现，后续如果要更接近影刀 RPA，建议按优先级继续做：

1. UI 元素录制器/拾取器：目前只能通过接口查找和返回推荐 selector，还没有像影刀那样鼠标点选页面元素并自动生成定位器的可视化捕获工具。
2. 流程变量和步骤间引用：`flow.run` 现在按顺序执行并返回每步结果，但还不支持 `${step1.data.xxx}` 这种变量表达式直接传给后续步骤。
3. 条件分支和循环块：当前 flow 只有顺序执行、重试、失败是否继续；还没有 if/else、while、for each、break/continue。
4. 异常处理块：还没有 try/catch/finally、失败截图自动归档、失败后跳转到指定步骤。
5. 文件下载等待和文件监听：还没有“等待下载完成、取最新下载文件、移动/重命名文件”的完整能力。
6. Excel 高级操作：当前支持基础读写；还没有按单元格读写、追加行、保留样式、透视表、公式刷新等高级能力。
7. OCR/文字点击：项目里有 OCR 预留，但还没有真正接入 cnOCR/PaddleOCR/Tesseract 并封装为 `ocr.find/click/extract`。
8. Windows 桌面控件自动化：已有 pywinauto 依赖，但尚未按窗口/控件树封装 `window.find/control.click/control.input`。
9. 弹窗/下载栏/系统对话框处理：还缺少浏览器弹窗、alert/confirm、文件选择框、系统保存框的统一动作。
10. 邮件、HTTP、数据库、定时触发：还没有封装邮件收发、HTTP 请求动作、SQL 查询动作、任务调度触发。
11. 日志与审计面板：目前只有接口返回和日志文件，没有流程运行历史表、步骤耗时、失败截图、回放视图。
12. AI 辅助能力：还没有“根据页面描述生成流程步骤”“根据截图识别下一步操作”的智能编排层。
