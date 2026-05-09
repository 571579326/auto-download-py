from app.schemas.desktop import HotkeyRequest, TypeTextRequest
from app.schemas.rpa import RpaKeyboardActionResponse, RpaKeyboardHotkeyRequest, RpaKeyboardPressRequest, RpaKeyboardTypeRequest
from app.services.desktop_service import desktop_service


class RpaKeyboardService:
    """RPA 键盘公共方法层。

    用于全局键盘输入、快捷键、单键按下。需要操作网页元素时优先使用 rpa_element_service.press。
    """

    @staticmethod
    def _pyautogui():
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError('未安装 pyautogui，请先执行 uv sync') from exc
        pyautogui.FAILSAFE = True
        return pyautogui

    def type_text(self, request: RpaKeyboardTypeRequest) -> RpaKeyboardActionResponse:
        """全局键盘输入文本。"""
        desktop_service.type_text(TypeTextRequest(text=request.text, intervalSeconds=request.intervalSeconds))
        return RpaKeyboardActionResponse(success=True, action='type', message='文本输入完成')

    def hotkey(self, request: RpaKeyboardHotkeyRequest) -> RpaKeyboardActionResponse:
        """执行组合快捷键，例如 ['ctrl', 's']。"""
        desktop_service.hotkey(HotkeyRequest(keys=request.keys, intervalSeconds=request.intervalSeconds))
        return RpaKeyboardActionResponse(success=True, action='hotkey', message=f'快捷键完成: {" + ".join(request.keys)}')

    def press(self, request: RpaKeyboardPressRequest) -> RpaKeyboardActionResponse:
        """按下单键或 pyautogui 支持的组合键。"""
        pyautogui = self._pyautogui()
        key = request.key.strip()
        if not key:
            raise ValueError('key不能为空')
        if '+' in key:
            keys = [item.strip() for item in key.split('+') if item.strip()]
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key)
        return RpaKeyboardActionResponse(success=True, action='press', message=f'按键完成: {key}')


rpa_keyboard_service = RpaKeyboardService()
