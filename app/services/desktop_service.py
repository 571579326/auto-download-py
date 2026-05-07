from app.desktop.windows_manager import windows_manager
from app.schemas.desktop import ActivateWindowRequest, ActivateWindowResponse, KeyboardActionResponse, HotkeyRequest, TypeTextRequest, WindowListResponse, WindowQueryRequest


class DesktopService:
    """给本地业务代码直接调用的桌面服务层。"""

    def list_windows(self, request: WindowQueryRequest | None = None) -> WindowListResponse:
        return windows_manager.list_windows(request or WindowQueryRequest())

    def activate_window(self, request: ActivateWindowRequest) -> ActivateWindowResponse:
        return windows_manager.activate_window(request)

    def type_text(self, request: TypeTextRequest) -> KeyboardActionResponse:
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError('未安装 pyautogui，请先执行 uv sync 或安装 requirements.txt') from exc
        pyautogui.write(request.text, interval=request.intervalSeconds)
        return KeyboardActionResponse(success=True, message='文本输入完成')

    def hotkey(self, request: HotkeyRequest) -> KeyboardActionResponse:
        if not request.keys:
            raise ValueError('keys不能为空')
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError('未安装 pyautogui，请先执行 uv sync 或安装 requirements.txt') from exc
        pyautogui.hotkey(*request.keys, interval=request.intervalSeconds)
        return KeyboardActionResponse(success=True, message=f'快捷键执行完成: {" + ".join(request.keys)}')


desktop_service = DesktopService()
