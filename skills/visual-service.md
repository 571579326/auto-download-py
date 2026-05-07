# visual-service skill

## 目标

提供本地可直接调用的屏幕/图像自动化 service，覆盖：

- 坐标点击。
- 模板图片点击。
- OCR 点击接口预留。

详细调用链见 `../docs/api-call-chain.md`。

## 关键文件

- `app/schemas/desktop.py`
- `app/visual/screen_manager.py`
- `app/services/visual_service.py`
- `app/api/desktop.py`

## 当前方法

- `click_position()`
- `click_image()`
- `ocr_click_text_reserved()`

## HTTP 入口

默认带 `/auto-download` 前缀：

- `POST /desktop/click/pos`
- `POST /desktop/click/image`
- `POST /desktop/click/ocr-text`

## click_position 规则

支持参数：

- `x`
- `y`
- `clicks`
- `intervalSeconds`
- `button`
- `durationSeconds`

实现方式：调用 `pyautogui.click()` 在屏幕坐标点击。

## click_image 规则

支持参数：

- `imagePath`
- `confidence`
- `regionLeft/Top/Width/Height`
- `grayscale`
- `timeoutMs`
- `retryIntervalMs`
- `clicks`
- `button`
- `moveDurationSeconds`

实现方式：

1. 用 `pyautogui.locateOnScreen()` 查找模板图。
2. 找到后取中心点。
3. 用 `pyautogui.click()` 点击。

## OCR 预留

当前只保留接口，不默认安装 `cnocr`。

后续推荐实现：

1. 截图。
2. 用 `cnocr` 识别目标文本框。
3. 算出中心坐标。
4. 调 `click_position()` 完成点击。

## 扩展顺序

1. `app/schemas/desktop.py`
2. `app/visual/screen_manager.py`
3. `app/services/visual_service.py`
4. `app/api/desktop.py`，仅在需要 HTTP 暴露时
5. 文档同步

## 注意

- 图片点击对 DPI 缩放、主题、分辨率、窗口遮挡敏感。
- 若图像定位失败，建议先排查截图模板与实际页面差异。
