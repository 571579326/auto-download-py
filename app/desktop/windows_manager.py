import os
import re
from typing import Any

from app.schemas.desktop import ActivateWindowRequest, ActivateWindowResponse, WindowInfo, WindowListResponse, WindowQueryRequest


def _require_windows() -> None:
    if os.name != 'nt':
        raise RuntimeError('桌面自动化当前仅支持 Windows')


class WindowsManager:
    def _desktop(self, backend: str):
        _require_windows()
        try:
            from pywinauto import Desktop
        except ImportError as exc:
            raise RuntimeError('未安装 pywinauto，请先执行 uv sync 或安装 requirements.txt') from exc
        return Desktop(backend=backend)

    @staticmethod
    def _safe_call(obj: Any, method_name: str, default=None):
        try:
            method = getattr(obj, method_name)
            return method()
        except Exception:
            return default

    @staticmethod
    def _build_window_info(window) -> WindowInfo:
        title = WindowsManager._safe_call(window, 'window_text', '') or ''
        class_name = WindowsManager._safe_call(window, 'class_name')
        process_id = WindowsManager._safe_call(window, 'process_id')
        is_visible = bool(WindowsManager._safe_call(window, 'is_visible', True))
        handle = int(getattr(window, 'handle', 0) or 0)
        return WindowInfo(
            handle=handle,
            title=title,
            className=class_name,
            processId=process_id,
            isVisible=is_visible,
        )

    def list_windows(self, request: WindowQueryRequest) -> WindowListResponse:
        desktop = self._desktop(request.backend)
        windows = desktop.windows()
        results: list[WindowInfo] = []
        regex = re.compile(request.titleRegex) if request.titleRegex else None

        for window in windows:
            info = self._build_window_info(window)
            if request.onlyVisible and not info.isVisible:
                continue
            if request.titleContains and request.titleContains not in info.title:
                continue
            if regex and not regex.search(info.title):
                continue
            results.append(info)
            if len(results) >= request.limit:
                break

        return WindowListResponse(total=len(results), windows=results)

    def activate_window(self, request: ActivateWindowRequest) -> ActivateWindowResponse:
        desktop = self._desktop(request.backend)
        kwargs = {}
        if request.handle is not None:
            kwargs['handle'] = request.handle
        if request.title is not None:
            kwargs['title'] = request.title
        if request.titleRegex is not None:
            kwargs['title_re'] = request.titleRegex
        if request.className is not None:
            kwargs['class_name'] = request.className
        if not kwargs:
            raise ValueError('activate_window 至少需要 handle/title/titleRegex/className 其中一个条件')

        try:
            window = desktop.window(**kwargs)
            window.wait('exists ready', timeout=max(request.timeoutMs / 1000, 1))
        except Exception as exc:
            raise RuntimeError(f'查找窗口失败: {exc}') from exc

        try:
            if request.restoreIfMinimized:
                try:
                    if self._safe_call(window, 'is_minimized', False):
                        window.restore()
                except Exception:
                    pass
            window.set_focus()
        except Exception as exc:
            raise RuntimeError(f'激活窗口失败: {exc}') from exc

        info = self._build_window_info(window)
        return ActivateWindowResponse(activated=True, handle=info.handle, title=info.title)


windows_manager = WindowsManager()
