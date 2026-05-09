# business-image-click skill

## 目标

提供业务公共图像点击服务，将"循环查找多张图像 -> 按 or/and 规则点击 -> 返回业务结果"的公共逻辑从 BusinessService 中抽离为独立服务层，避免各个业务接口重复拼装 ClickImageRequest 和重复处理异常。

详细调用链见 `../docs/api-call-chain.md`。

## 关键文件

- `app/services/business_image_click_service.py`
- `app/utils/image_utils.py`

## 核心数据结构

### BusinessImageClickOptions

| 字段 | 类型 | 说明 |
|------|------|------|
| `enabled` | bool | 是否启用图像点击 |
| `image_paths` | list[str] | 待匹配图像路径列表 |
| `match_mode` | str | 匹配模式：`or`（任一匹配即点击） / `and`（全部匹配后依次点击） |
| `confidence` | float | 图像匹配置信度（0~1） |
| `timeout_ms` | int | 总超时时间（毫秒） |
| `retry_interval_ms` | int | 重试间隔（毫秒） |
| `click_offset_x` | int \| None | 点击 X 偏移（相对匹配图片区域左上角） |
| `click_offset_y` | int \| None | 点击 Y 偏移（相对匹配图片区域左上角） |

### BusinessImageClickResult

| 字段 | 类型 | 说明 |
|------|------|------|
| `clicked` | bool | 是否成功点击 |
| `skipped` | bool | 是否跳过（未启用或未配置图像路径） |
| `image_paths` | list[str] | 实际参与匹配的图像路径 |
| `match_mode` | str | 实际使用的匹配模式 |
| `clicked_images` | list[dict] | 已点击的图像信息列表 |
| `error` | str \| None | 异常信息（失败时填充） |
| `skip_reason` | str \| None | 跳过原因（跳过时填充） |
| `click_offset_x` | int \| None | 实际使用的 X 偏移 |
| `click_offset_y` | int \| None | 实际使用的 Y 偏移 |

## 核心方法

### build_auto_click_options(click_offset_x, click_offset_y)

基于当前 .env 配置构造业务图像点击参数。自动解析点击偏移优先级：
1. 接口传入 clickOffsetX/clickOffsetY
2. .env 配置 AUTO_CLICK_IMAGE_CLICK_OFFSET_X/Y
3. 全部为空时，底层默认点击匹配框中心点

### resolve_click_offset(click_offset_x, click_offset_y)

解析图像点击偏移，与 build_auto_click_options 共用偏移优先级逻辑。

### find_and_click_images(options, scene)

公共业务方法：循环查找图像并点击。

行为约定：
- `enabled=false` 或 `image_paths` 为空时返回 `clicked=False, skipped=True`，不抛错
- 找到并点击时返回 `clicked=True`，附带 `clicked_images`
- 超时未找到或点击失败时返回 `clicked=False` + `error`，不中断主业务流程
- `scene` 参数用于日志标识调用场景，如 `page-flow:playwright_once:acg18`

## 调用方

- `app/services/business_service.py`（/biz/page-flow、/biz/page-flow-selenium）

## 扩展顺序

业务图像点击能力变更时，按以下顺序操作：

1. `app/services/business_image_click_service.py`：修改数据类或服务方法
2. `app/services/business_service.py`：更新调用方（如需调整结果消费逻辑）
3. `docs/api-call-chain.md` 和相关 skills 文档同步

## 注意

- 本服务不直接调用桌面截图或鼠标点击能力，通过 `app/utils/image_utils.py` 的 `click_images_until_found` 中转
- 偏移值 `click_offset_x/click_offset_y` 是相对"匹配到的图片区域左上角"的偏移，不是相对屏幕左上角
- 本服务返回的业务结果不会导致 HTTP 500，图像点击失败通过 `clicked: false` + `error` 返回
- 本服务实例为模块级单例：`business_image_click_service`
