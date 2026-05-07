import os
import time

from app.schemas.desktop import (
    ClickImageRequest,
    ClickImageResponse,
    ClickPositionRequest,
    ClickPositionResponse,
    OcrClickTextRequest,
    OcrClickTextResponse,
)


def _require_windows() -> None:
    if os.name != 'nt':
        raise RuntimeError('图像/屏幕自动化当前仅支持 Windows')


class ScreenManager:
    def _pyautogui(self):
        _require_windows()
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError('未安装 pyautogui，请先执行 uv sync 或安装 requirements.txt') from exc
        pyautogui.FAILSAFE = True
        return pyautogui

    @staticmethod
    def _build_region(request: ClickImageRequest):
        fields = [request.regionLeft, request.regionTop, request.regionWidth, request.regionHeight]
        if all(value is None for value in fields):
            return None
        if any(value is None for value in fields):
            raise ValueError('regionLeft/regionTop/regionWidth/regionHeight 需要同时传入，或全部不传')
        return (request.regionLeft, request.regionTop, request.regionWidth, request.regionHeight)

    def click_position(self, request: ClickPositionRequest) -> ClickPositionResponse:
        pyautogui = self._pyautogui()
        pyautogui.click(
            x=request.x,
            y=request.y,
            clicks=request.clicks,
            interval=request.intervalSeconds,
            button=request.button,
            duration=request.durationSeconds,
        )
        return ClickPositionResponse(
            clicked=True,
            x=request.x,
            y=request.y,
            clicks=request.clicks,
            button=request.button,
        )

    def click_image(self, request: ClickImageRequest) -> ClickImageResponse:
        if not os.path.exists(request.imagePath):
            raise ValueError(f'imagePath不存在: {request.imagePath}')

        pyautogui = self._pyautogui()
        region = self._build_region(request)
        deadline = time.time() + request.timeoutMs / 1000
        last_error: Exception | None = None

        while time.time() < deadline:
            try:
                box = pyautogui.locateOnScreen(
                    request.imagePath,
                    confidence=request.confidence,
                    region=region,
                    grayscale=request.grayscale,
                )
                if box is not None:
                    center = pyautogui.center(box)
                    pyautogui.click(
                        x=center.x,
                        y=center.y,
                        clicks=request.clicks,
                        interval=request.intervalSeconds,
                        button=request.button,
                        duration=request.moveDurationSeconds,
                    )
                    return ClickImageResponse(
                        clicked=True,
                        centerX=int(center.x),
                        centerY=int(center.y),
                        left=int(box.left),
                        top=int(box.top),
                        width=int(box.width),
                        height=int(box.height),
                        imagePath=request.imagePath,
                        confidence=request.confidence,
                    )
            except Exception as exc:
                last_error = exc
            time.sleep(request.retryIntervalMs / 1000)

        if last_error is not None:
            raise RuntimeError(f'按图片点击失败: {last_error}') from last_error
        raise RuntimeError(
            f'超时未找到目标图片: imagePath={request.imagePath}, confidence={request.confidence}, region={region}'
        )

    def ocr_click_text_reserved(self, request: OcrClickTextRequest) -> OcrClickTextResponse:
        message = (
            '已预留 OCR 点击接口，当前未默认实现。后续可接入 cnOCR：'
            '先截图，再识别文本框位置，再结合 PyAutoGUI/Windows 层完成点击。'
            f' 当前参数: text={request.text}, contains={request.contains}, confidence={request.confidence}'
        )
        return OcrClickTextResponse(reserved=True, message=message)


screen_manager = ScreenManager()
