# 开发指南

## 总原则

- 新能力优先沿用现有分层，不在 API 层写核心逻辑。
- 本地业务调用入口放在 `app/services/*.py`。
- HTTP API 只做参数接收、schema 绑定、线程池转调和 `Result` 响应封装。
- 数据库会话不要暴露给上层业务代码。
- 当前没有 Vue 前端和 Java mapper/xml，不要在文档或代码中假定这些目录存在。

## 新增浏览器能力

改动顺序：

1. 在 `app/schemas/browser.py` 定义请求/响应模型。
2. 在 `app/browser/manager.py` 实现核心逻辑和必要的数据库同步。
3. 在 `app/services/browser_service.py` 增加本地 service 方法。
4. 如果需要 HTTP 暴露，在 `app/api/browser.py` 增加路由，并用 `run_in_threadpool()` 调 service。
5. 更新 `docs/api-call-chain.md` 和相关 skills 文档。

约束：

- 同步 Playwright API 不要直接在 FastAPI async 路由里执行。
- 页面定位继续遵守 `pageId` 优先、`urlContains` 次之、默认 active/最近页面的规则。
- 涉及窗口或页面状态变化时，同步更新 `ad_browser_window` / `ad_browser_page`。

## 新增桌面窗口能力

改动顺序：

1. 在 `app/schemas/desktop.py` 定义请求/响应模型。
2. 在 `app/desktop/windows_manager.py` 实现 pywinauto 相关逻辑。
3. 在 `app/services/desktop_service.py` 增加 service 方法。
4. 如果需要 HTTP 暴露，在 `app/api/desktop.py` 增加路由。
5. 更新文档。

约束：

- 需要目标窗口聚焦的能力，应在文档或返回信息中明确前置条件。
- Windows 平台检查和依赖缺失错误应尽量在 manager/service 层给出清晰信息。

## 新增图像/屏幕能力

改动顺序：

1. 在 `app/schemas/desktop.py` 定义请求/响应模型。
2. 在 `app/visual/screen_manager.py` 实现坐标、截图、模板图或 OCR 逻辑。
3. 在 `app/services/visual_service.py` 增加 service 方法。
4. 如果需要 HTTP 暴露，在 `app/api/desktop.py` 增加路由。
5. 更新文档。

约束：

- 图像匹配失败时应返回足够排查的信息，例如模板路径、置信度、region、timeout。
- OCR 当前是预留能力；真正接入 `cnocr` 时，应明确依赖安装、截图范围、文本匹配规则和点击坐标计算方式。

## 新增业务图像点击能力

改动顺序：

1. 在 `app/services/business_image_click_service.py` 修改 BusinessImageClickOptions/BusinessImageClickResult 数据类或 BusinessImageClickService 方法。
2. 在 `app/services/business_service.py` 更新调用方（如需调整结果消费逻辑）。
3. 更新 `docs/api-call-chain.md` 和相关 skills 文档。

## API 命名和响应

- 路由路径使用当前风格：`/browser/...`、`/desktop/...`。
- 完整 HTTP 路径默认加 `/auto-download` 前缀。
- 响应统一使用 `app.schemas.common.Result`。
- 参数校验优先放在 Pydantic schema；依赖运行时状态的校验放在 manager/service。

## 错误处理

`app/main.py` 已统一处理：

- `ValueError` -> HTTP 400
- `RuntimeError` -> HTTP 500，并记录日志
- 其他异常 -> HTTP 500，并记录日志

新增代码应优先抛出语义明确的 `ValueError` 或 `RuntimeError`，不要吞掉底层异常导致排查困难。

## 文档同步

新增或调整能力后至少同步：

- `README.md` 的能力/API 总览。
- `docs/api-call-chain.md` 的接口映射。
- `AGENT.md` 的维护规则或边界。
- 对应的 `skills/*.md`。
