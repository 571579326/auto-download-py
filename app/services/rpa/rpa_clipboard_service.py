import ctypes
import os

from app.schemas.rpa import RpaClipboardResponse, RpaClipboardSetRequest, RpaKeyboardHotkeyRequest
from app.services.rpa.rpa_keyboard_service import rpa_keyboard_service


class RpaClipboardService:
    """RPA 剪贴板公共方法层。

    适合大量文本输入：先写入剪贴板，再粘贴到目标位置，比逐字输入更稳定。
    这里优先使用成熟第三方库 pyperclip；如果本机未安装或不可用，再回退到 Windows 原生剪贴板 API。
    """

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    def set_text(self, request: RpaClipboardSetRequest) -> RpaClipboardResponse:
        """设置系统剪贴板文本。"""
        text = request.text or ''
        if self._try_pyperclip_set(text):
            return RpaClipboardResponse(success=True, text=text, message='剪贴板写入完成(pyperclip)')
        self._windows_set_text(text)
        return RpaClipboardResponse(success=True, text=text, message='剪贴板写入完成(Windows API)')

    def get_text(self) -> RpaClipboardResponse:
        """读取系统剪贴板文本。"""
        pyperclip_text = self._try_pyperclip_get()
        if pyperclip_text is not None:
            return RpaClipboardResponse(success=True, text=pyperclip_text, message='剪贴板读取完成(pyperclip)')
        return RpaClipboardResponse(success=True, text=self._windows_get_text(), message='剪贴板读取完成(Windows API)')

    def paste(self) -> RpaClipboardResponse:
        """执行 Ctrl+V 粘贴。"""
        rpa_keyboard_service.hotkey(RpaKeyboardHotkeyRequest(keys=['ctrl', 'v']))
        return RpaClipboardResponse(success=True, text=None, message='粘贴快捷键已执行')

    @staticmethod
    def _try_pyperclip_set(text: str) -> bool:
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except Exception:
            return False

    @staticmethod
    def _try_pyperclip_get() -> str | None:
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            return None

    @staticmethod
    def _require_windows() -> None:
        if os.name != 'nt':
            raise RuntimeError('剪贴板公共方法当前需要 pyperclip 或 Windows 原生剪贴板 API')

    def _windows_set_text(self, text: str) -> None:
        self._require_windows()
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.restype = ctypes.c_void_p
        user32.SetClipboardData.restype = ctypes.c_void_p
        data = text + '\0'
        byte_size = len(data.encode('utf-16-le'))

        if not user32.OpenClipboard(None):
            raise RuntimeError('打开剪贴板失败')
        try:
            user32.EmptyClipboard()
            handle = kernel32.GlobalAlloc(self.GMEM_MOVEABLE, byte_size)
            if not handle:
                raise RuntimeError('分配剪贴板内存失败')
            locked = kernel32.GlobalLock(handle)
            if not locked:
                raise RuntimeError('锁定剪贴板内存失败')
            try:
                ctypes.memmove(locked, data.encode('utf-16-le'), byte_size)
            finally:
                kernel32.GlobalUnlock(handle)
            if not user32.SetClipboardData(self.CF_UNICODETEXT, handle):
                raise RuntimeError('写入剪贴板失败')
        finally:
            user32.CloseClipboard()

    def _windows_get_text(self) -> str:
        self._require_windows()
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.GetClipboardData.restype = ctypes.c_void_p
        kernel32.GlobalLock.restype = ctypes.c_void_p
        if not user32.IsClipboardFormatAvailable(self.CF_UNICODETEXT):
            return ''
        if not user32.OpenClipboard(None):
            raise RuntimeError('打开剪贴板失败')
        try:
            handle = user32.GetClipboardData(self.CF_UNICODETEXT)
            if not handle:
                return ''
            locked = kernel32.GlobalLock(handle)
            if not locked:
                raise RuntimeError('锁定剪贴板内存失败')
            try:
                return ctypes.wstring_at(locked)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()


rpa_clipboard_service = RpaClipboardService()
