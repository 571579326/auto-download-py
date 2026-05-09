from app.schemas.desktop import ClickPositionRequest
from app.schemas.rpa import (
    RpaMouseActionResponse,
    RpaMouseClickRequest,
    RpaMouseDragRequest,
    RpaMouseMoveRequest,
    RpaMouseScrollRequest,
)
from app.services.visual_service import visual_service


class RpaMouseService:
    """RPA 鼠标公共方法层。

    用于坐标点击、移动、拖拽、滚轮等桌面级操作。坐标基于屏幕左上角。
    """

    @staticmethod
    def _pyautogui():
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError('未安装 pyautogui，请先执行 uv sync') from exc
        pyautogui.FAILSAFE = True
        return pyautogui

    def click(self, request: RpaMouseClickRequest):
        """按屏幕坐标点击。"""
        return visual_service.click_position(
            ClickPositionRequest(
                x=request.x,
                y=request.y,
                clicks=request.clicks,
                intervalSeconds=request.intervalSeconds,
                button=request.button,
                durationSeconds=request.durationSeconds,
            )
        )

    def move(self, request: RpaMouseMoveRequest) -> RpaMouseActionResponse:
        """移动鼠标到指定坐标。"""
        pyautogui = self._pyautogui()
        pyautogui.moveTo(request.x, request.y, duration=request.durationSeconds)
        return RpaMouseActionResponse(success=True, action='move', x=request.x, y=request.y)

    def drag(self, request: RpaMouseDragRequest) -> RpaMouseActionResponse:
        """从起点拖拽到终点。"""
        pyautogui = self._pyautogui()
        pyautogui.moveTo(request.fromX, request.fromY)
        pyautogui.dragTo(request.toX, request.toY, duration=request.durationSeconds, button=request.button)
        return RpaMouseActionResponse(success=True, action='drag', x=request.toX, y=request.toY)

    def scroll(self, request: RpaMouseScrollRequest) -> RpaMouseActionResponse:
        """执行鼠标滚轮。正数向上，负数向下。"""
        pyautogui = self._pyautogui()
        if request.x is not None and request.y is not None:
            pyautogui.moveTo(request.x, request.y)
        pyautogui.scroll(request.clicks)
        return RpaMouseActionResponse(success=True, action='scroll', message=f'滚动完成: {request.clicks}')


rpa_mouse_service = RpaMouseService()
