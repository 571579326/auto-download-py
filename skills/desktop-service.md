# desktop-service skill

## 目标

提供本地可直接调用的桌面自动化 service，覆盖：

- 枚举窗口。
- 激活窗口。
- 键盘输入。
- 快捷键发送。
- 与视觉点击配合使用。

详细调用链见 `../docs/api-call-chain.md`。

## 关键文件

- `app/schemas/desktop.py`
- `app/desktop/windows_manager.py`
- `app/services/desktop_service.py`
- `app/api/desktop.py`

## 当前方法

- `list_windows()`
- `activate_window()`
- `type_text()`
- `hotkey()`

## HTTP 入口

默认带 `/auto-download` 前缀：

- `GET /desktop/windows`
- `POST /desktop/window/activate`
- `POST /desktop/keyboard/type`
- `POST /desktop/keyboard/hotkey`

## 实现说明

### list_windows

基于 `pywinauto.Desktop(backend=...)` 枚举窗口。

### activate_window

支持条件：

- `handle`
- `title`
- `titleRegex`
- `className`

至少传一个定位条件。

### type_text / hotkey

当前用 `pyautogui` 发送全局键盘操作，所以要先确保目标窗口已激活。

## 扩展顺序

1. `app/schemas/desktop.py`
2. `app/desktop/windows_manager.py`
3. `app/services/desktop_service.py`
4. `app/api/desktop.py`，仅在需要 HTTP 暴露时
5. 文档同步

## 注意

- 当前按 Windows 设计。
- 复杂控件树操作还未下沉到更细粒度 API。
- 后续如果需要点击按钮、读取控件值，可继续在 `windows_manager.py` 增强。
